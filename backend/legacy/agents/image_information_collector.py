"""Image Information Collector.

This script analyzes product images for a given SKU. It performs:
- Per-image vision analysis via OpenAI (strict JSON with retries)
- Local metrics (brightness, contrast, entropy, sharpness, colorfulness, etc.)
- Perceptual hash deduplication (pHash, Hamming distance <= 5)
- Caching by (sku, filename, sha1) in `image_analysis.jsonl`
- Grouped JSON output per SKU to `out/sku_summary/<SKU>.images.json`

It intentionally avoids any decisioning, enhancement prompts, or marketplace logic.
CLI arguments remain minimal: provide a SKU and an images directory containing that SKU's images.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image

# Optional: only imported when actually calling OpenAI
try:  # pragma: no cover - imported lazily for environments without OpenAI
	from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
	OpenAI = None

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Load environment variables from .env file
try:
	from dotenv import load_dotenv
	load_dotenv(ROOT / ".env")
except ImportError:
	pass

import config  # noqa: E402
from utils import (  # noqa: E402
	aspect_ratio,
	brightness_contrast_entropy,
	collect_image_paths,
	compute_colorfulness,
	compute_sha1,
	exif_orientation,
	hamming_distance,
	laplacian_sharpness,
	load_image_rgb,
	phash,
	preprocess_image_to_bytes,
	white_border_ratio,
)


# -----------------------------
# Data structures
# -----------------------------


@dataclass
class ImageRecord:
	sku: str
	filename: str
	sha1: str
	capture_type: str
	angle: str
	composition: str
	arrangement: str
	content_type: str
	is_product: bool
	notes: str
	quality: float
	bg_cleanliness: float
	crop_ok: bool
	shadow_ok: bool
	framing_ok: bool
	measure_text: str
	measure_value: str
	measure_unit: str
	measure_confidence: float
	measure_cm: Optional[float]
	material_guess: str
	material_confidence: float
	color_names: List[str]
	pattern: str
	pattern_confidence: float
	logos_present: str
	logos_confidence: float
	lighting_desc: str
	lighting_confidence: float
	bg_type: str
	bg_confidence: float
	# local metrics
	brightness: float
	contrast: float
	entropy: float
	sharpness: float
	colorfulness: float
	resolution: Tuple[int, int]
	aspect_ratio: float
	white_border_ratio: float
	exif_orientation: Optional[int]
	file_size: int
	phash: str

	def to_dict(self) -> Dict[str, Any]:
		d = asdict(self)
		d["resolution"] = {"width": self.resolution[0], "height": self.resolution[1]}
		return d


# -----------------------------
def load_cache(cache_path: Path) -> Dict[Tuple[str, str, str], Dict[str, Any]]:
	cache: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
	if not cache_path.exists():
		return cache
	with cache_path.open("r", encoding="utf-8") as f:
		for line in f:
			line = line.strip()
			if not line:
				continue
			try:
				entry = json.loads(line)
				key = (entry.get("sku"), entry.get("filename"), entry.get("sha1"))
				cache[key] = entry
			except Exception:
				continue
	return cache


def append_cache(cache_path: Path, record: ImageRecord) -> None:
	with cache_path.open("a", encoding="utf-8") as f:
		f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")


def encode_image_base64(path: Path) -> str:
	b = preprocess_image_to_bytes(path)
	return base64.b64encode(b).decode("utf-8")


# -----------------------------
# OpenAI Vision interaction
# -----------------------------


REQUIRED_KEYS = {
	"capture_type",
	"angle",
	"composition",
	"arrangement",
	"content_type",
	"is_product",
	"notes",
	"quality",
	"bg_cleanliness",
	"crop_ok",
	"shadow_ok",
	"framing_ok",
	"measure_text",
	"measure_value",
	"measure_unit",
	"measure_confidence",
	"measure_cm",
	"material_guess",
	"material_confidence",
	"color_names",
	"pattern",
	"pattern_confidence",
	"logos_present",
	"logos_confidence",
	"lighting_desc",
	"lighting_confidence",
	"bg_type",
	"bg_confidence",
}


def parse_strict_json(text: str) -> Dict[str, Any]:
	cleaned = text.strip()
	if cleaned.startswith("```"):
		cleaned = cleaned.strip("`")
		cleaned = cleaned.replace("json", "", 1).strip()
	data = json.loads(cleaned)
	missing = [k for k in REQUIRED_KEYS if k not in data]
	if missing:
		raise ValueError(f"Missing keys: {missing}")
	return data


def call_openai_vision(image_b64: str) -> Dict[str, Any]:
	if OpenAI is None:
		raise RuntimeError("openai package not available")

	api_key = os.getenv("OPENAI_API_KEY")
	if not api_key:
		raise RuntimeError("OPENAI_API_KEY environment variable not set")

	client = OpenAI(api_key=api_key)
	prompt = (
		"Return ONLY JSON with these fields: capture_type ('stock'|'phone'), angle one of"
		" [diagonal_45, front, left, right, top, back, overview, detail, on_foot, unusable],"
		" composition, arrangement, content_type, is_product (true/false), notes, quality (0..1),"
		" bg_cleanliness (0..1), crop_ok (bool), shadow_ok (bool), framing_ok (bool),"
		" measure_text, measure_value, measure_unit, measure_confidence (0..1), measure_cm (numeric or null),"
		" material_guess, material_confidence (0..1), color_names (max 3), pattern, pattern_confidence (0..1),"
		" logos_present, logos_confidence (0..1), lighting_desc, lighting_confidence (0..1),"
		" bg_type, bg_confidence (0..1). Do not include any other text."
	)

	for attempt in range(3):
		try:
			resp = client.chat.completions.create(
				model="gpt-4o-mini",
				messages=[
					{
						"role": "user",
						"content": [
							{"type": "text", "text": prompt},
							{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
						],
					}
				],
				max_tokens=700,
				temperature=0.1,
			)
			content = resp.choices[0].message.content or ""
			data = parse_strict_json(content)
			return data
		except Exception as exc:
			if attempt == 2:
				raise
			sleep = 2**attempt
			print(f"OpenAI parse error (attempt {attempt+1}): {exc}; retrying in {sleep}s")
			time.sleep(sleep)
	raise RuntimeError("Failed to parse OpenAI vision response")


# -----------------------------
# Image preparation phase: load image + compute local metrics (no API)
def prepare_image_for_analysis(
	path: Path, 
	sku: str, 
	cache: Dict[Tuple[str, str, str], Dict[str, Any]], 
	phashes: List[str]
) -> Optional[Dict[str, Any]]:
	"""Prepare image: check cache, load, dedup check, encode, compute metrics (FAST - all local).
	
	Returns dict with image data or None if cached/duplicate.
	"""
	# Fast check: compute sha1 for cache lookup
	load_start = time.time()
	image = load_image_rgb(path)
	load_time = time.time() - load_start
	
	sha1 = compute_sha1(path)
	key = (sku, path.name, sha1)

	# Check cache first
	if key in cache:
		cached = cache[key]
		resolution = cached.get("resolution")
		if isinstance(resolution, dict):
			cached["resolution"] = (resolution.get("width", 0), resolution.get("height", 0))
		print(f"    [CACHE] {path.name}")
		return {"status": "cached", "record": ImageRecord(**cached), "path": path, "load_time": load_time}  # type: ignore[arg-type]

	# Quick phash compute for deduplication
	phash_start = time.time()
	current_phash = phash(image)
	phash_time = time.time() - phash_start
	
	for existing in phashes:
		if hamming_distance(existing, current_phash) <= 5:
			print(f"    [DUPE] {path.name}")
			return {"status": "duplicate", "path": path, "load_time": load_time, "phash_time": phash_time}

	# Compute ALL local metrics NOW (before parallelization)
	metrics_start = time.time()
	brightness, contrast, ent = brightness_contrast_entropy(image)
	sharp = laplacian_sharpness(image)
	colorf = compute_colorfulness(image)
	size = image.size
	white_ratio = white_border_ratio(image)
	orientation = exif_orientation(image)
	file_size = path.stat().st_size
	metrics_time = time.time() - metrics_start
	
	# Encode image for OpenAI (this is fast)
	encode_start = time.time()
	b64 = encode_image_base64(path)
	encode_time = time.time() - encode_start
	
	print(f"    [OK] {path.name}")
	
	# Return ready-to-analyze data with all local work done
	return {
		"status": "ready",
		"path": path,
		"sha1": sha1,
		"key": key,
		"image": image,
		"current_phash": current_phash,
		"b64": b64,
		"brightness": brightness,
		"contrast": contrast,
		"entropy": ent,
		"sharpness": sharp,
		"colorfulness": colorf,
		"size": size,
		"white_ratio": white_ratio,
		"orientation": orientation,
		"file_size": file_size,
		"load_time": load_time,
		"phash_time": phash_time,
		"metrics_time": metrics_time,
		"encode_time": encode_time,
	}


# OpenAI vision call ONLY (metrics already computed in Phase 1)
def call_openai_for_image(prep_data: Dict[str, Any]) -> Dict[str, Any]:
	"""Call OpenAI vision API ONLY (all prep work done in Phase 1). Run in thread pool."""
	path = prep_data["path"]
	
	# Call OpenAI API - this is the ONLY blocking operation in the thread pool
	api_start = time.time()
	b64 = prep_data["b64"]  # Already encoded in Phase 1
	ai = call_openai_vision(b64)
	api_time = time.time() - api_start
	prep_data["api_response"] = ai
	prep_data["api_time"] = api_time
	return prep_data


# Combine results into ImageRecord
def finalize_image_analysis(
	prep_data: Dict[str, Any],
	cache_path: Path,
	phashes: List[str]
) -> Optional[ImageRecord]:
	"""Convert prep data + API response into ImageRecord."""
	path = prep_data["path"]
	
	if prep_data["status"] == "cached":
		print(f"    [CACHE HIT] {path.name}")
		return prep_data["record"]
	
	if prep_data["status"] == "duplicate":
		print(f"    [DUPE] {path.name}")
		return None
	
	# Skip if API call failed (no response)
	if "api_response" not in prep_data:
		print(f"    [SKIP] {path.name} (no API response)")
		return None
	
	ai = prep_data["api_response"]
	api_time = prep_data["api_time"]
	load_time = prep_data["load_time"]
	
	try:
		measure_cm_val = ai.get("measure_cm")
		measure_cm = float(measure_cm_val) if measure_cm_val not in (None, "") else None
	except Exception:
		measure_cm = None

	record = ImageRecord(
		sku=prep_data["key"][0],
		filename=path.name,
		sha1=prep_data["sha1"],
		capture_type=str(ai.get("capture_type", "")),
		angle=str(ai.get("angle", "")),
		composition=str(ai.get("composition", "")),
		arrangement=str(ai.get("arrangement", "")),
		content_type=str(ai.get("content_type", "")),
		is_product=bool(ai.get("is_product", False)),
		notes=str(ai.get("notes", "")),
		quality=float(ai.get("quality", 0.0)),
		bg_cleanliness=float(ai.get("bg_cleanliness", 0.0)),
		crop_ok=bool(ai.get("crop_ok", False)),
		shadow_ok=bool(ai.get("shadow_ok", False)),
		framing_ok=bool(ai.get("framing_ok", False)),
		measure_text=str(ai.get("measure_text", "")),
		measure_value=str(ai.get("measure_value", "")),
		measure_unit=str(ai.get("measure_unit", "")),
		measure_confidence=float(ai.get("measure_confidence", 0.0)),
		measure_cm=measure_cm,
		material_guess=str(ai.get("material_guess", "")),
		material_confidence=float(ai.get("material_confidence", 0.0)),
		color_names=[str(c) for c in ai.get("color_names", [])][:3],
		pattern=str(ai.get("pattern", "")),
		pattern_confidence=float(ai.get("pattern_confidence", 0.0)),
		logos_present=str(ai.get("logos_present", "")),
		logos_confidence=float(ai.get("logos_confidence", 0.0)),
		lighting_desc=str(ai.get("lighting_desc", "")),
		lighting_confidence=float(ai.get("lighting_confidence", 0.0)),
		bg_type=str(ai.get("bg_type", "")),
		bg_confidence=float(ai.get("bg_confidence", 0.0)),
		brightness=prep_data.get("brightness", 0),
		contrast=prep_data.get("contrast", 0),
		entropy=prep_data.get("entropy", 0),
		sharpness=prep_data.get("sharpness", 0),
		colorfulness=prep_data.get("colorfulness", 0),
		resolution=prep_data.get("size", (0, 0)),
		aspect_ratio=aspect_ratio(prep_data.get("size", (0, 0))),
		white_border_ratio=prep_data.get("white_ratio", 0),
		exif_orientation=prep_data.get("orientation", 0),
		file_size=prep_data.get("file_size", 0),
		phash=prep_data["current_phash"],
	)

	append_cache(cache_path, record)
	phashes.append(prep_data["current_phash"])
	print(f"    [SUCCESS] {path.name} (load={prep_data['load_time']:.2f}s, api={api_time:.2f}s)")
	return record
	print(f"    [SUCCESS] {path.name} (load={load_time:.2f}s, phash={phash_time:.2f}s, openai={api_time:.2f}s)")
	return record


def summarize(records: List[ImageRecord]) -> Dict[str, Any]:
	has_stock = any(r.capture_type == "stock" for r in records)
	has_phone = any(r.capture_type == "phone" for r in records)
	count_stock = sum(1 for r in records if r.capture_type == "stock")
	count_phone = sum(1 for r in records if r.capture_type == "phone")
	angles = sorted({r.angle for r in records if r.angle})

	stock = [r.to_dict() for r in records if r.capture_type == "stock"]
	phone = [r.to_dict() for r in records if r.capture_type == "phone"]

	return {
		"schema_version": "1.0",
		"summary": {
			"has_stock": has_stock,
			"has_phone": has_phone,
			"count_stock": count_stock,
			"count_phone": count_phone,
			"angles_covered": angles,
		},
		"stock": stock,
		"phone": phone,
	}


# -----------------------------
# CLI and main
# -----------------------------


def find_images_dir_for_sku(sku: str) -> Optional[Path]:
	for base in config.IMAGE_FOLDER_PATHS:
		base_path = base if base.is_absolute() else (config.PROJECT_ROOT / base)
		candidate = base_path / sku
		if candidate.exists() and candidate.is_dir():
			return candidate
	return None


def process_single_sku(
	sku: str,
	images_dir: Path,
	cache: Dict[Tuple[str, str, str], Dict[str, Any]],
	cache_path: Path,
	out_dir: Path,
) -> None:
	sku_start = time.time()
	print(f"\n[SKU] {sku}")
	
	if not images_dir.exists():
		print(f"  ✗ Images directory not found: {images_dir}")
		return

	image_paths = collect_image_paths(images_dir)
	if not image_paths:
		print(f"  ✗ No images found")
		return

	print(f"  Found {len(image_paths)} image(s)")
	
	phashes: List[str] = []
	records: List[ImageRecord] = []

	# Phase 1: Prepare all images (load, dedup check - FAST)
	print(f"  [PHASE 1] Loading and preparing {len(image_paths)} images...")
	prep_start = time.time()
	prep_data_list = []
	for idx, path in enumerate(image_paths, 1):
		prep = prepare_image_for_analysis(path, sku, cache, phashes)
		if prep:
			prep_data_list.append(prep)
		# Show progress every image
		print(f"    [{idx}/{len(image_paths)}]", end="\r")
	prep_time = time.time() - prep_start
	
	# Count results from phase 1
	cached = [p for p in prep_data_list if p["status"] == "cached"]
	duplicates = [p for p in prep_data_list if p["status"] == "duplicate"]
	to_analyze = [p for p in prep_data_list if p["status"] == "ready"]
	
	print(f"  ✓ Prepared: {len(cached)} cached, {len(duplicates)} duplicates, {len(to_analyze)} to analyze ({prep_time:.2f}s)")
	
	# Add cached records to results
	for prep in cached:
		if prep["record"]:
			records.append(prep["record"])
	
	# Phase 2: Parallel OpenAI API calls for images needing analysis
	if to_analyze:
		print(f"  [PHASE 2] Parallel OpenAI analysis for {len(to_analyze)} image(s)...")
		api_start = time.time()
		
		with ThreadPoolExecutor(max_workers=3) as executor:
			futures = {executor.submit(call_openai_for_image, prep): prep for prep in to_analyze}
			completed = 0
			for future in as_completed(futures):
				completed += 1
				prep = futures[future]
				try:
					prep = future.result()
					remaining = len(to_analyze) - completed
					print(f"    [{completed}/{len(to_analyze)}] {prep['path'].name} (API: {prep['api_time']:.2f}s) - {remaining} remaining")
				except Exception as exc:
					print(f"    [ERROR] {prep['path'].name}: {exc}")
		
		api_total = time.time() - api_start
		print(f"  ✓ OpenAI analysis complete ({api_total:.2f}s for {len(to_analyze)} images in parallel)")
		
		# Phase 3: Finalize all analyzed images
		print(f"  [PHASE 3] Finalizing records...")
		for prep in to_analyze:
			rec = finalize_image_analysis(prep, cache_path, phashes)
			if rec:
				records.append(rec)
	
	# Write results
	print(f"  [WRITE] Saving {len(records)} records to JSON...")
	summary = summarize(records)
	out_path = out_dir / f"{sku}.images.json"
	out_path.parent.mkdir(parents=True, exist_ok=True)
	with out_path.open("w", encoding="utf-8") as f:
		json.dump(summary, f, ensure_ascii=False, indent=2)
	
	product_path = config.PRODUCTS_FOLDER_PATH / f"{sku}.json"
	try:
		with product_path.open("r", encoding="utf-8") as pf:
			existing_product = json.load(pf)
	except Exception:
		existing_product = {sku: {}}

	if sku not in existing_product or not isinstance(existing_product.get(sku), dict):
		existing_product[sku] = {}
	existing_product[sku]["Images"] = summary

	with product_path.open("w", encoding="utf-8") as pf:
		json.dump(existing_product, pf, ensure_ascii=False, indent=2)

	total_time = time.time() - sku_start
	print(f"  ✓ Complete: {len(records)} records in {total_time:.2f}s total")
	print(f"  Saved {out_path} and updated {product_path}")


def main() -> None:
	parser = argparse.ArgumentParser(description="Collect image information for a SKU")
	parser.add_argument("sku", nargs="?", help="SKU identifier")
	parser.add_argument("images_dir", nargs="?", help="Directory containing images for this SKU")
	parser.add_argument("--cache", default=ROOT / "agents" / "image_analysis.jsonl", help="Path to JSONL cache", type=Path)
	parser.add_argument("--out", default=ROOT / "out" / "sku_summary", help="Output folder", type=Path)
	parser.add_argument("--auto-missing", action="store_true", help="Scan products without Images and analyze if images folder exists")
	args = parser.parse_args()

	cache_path: Path = args.cache
	out_dir: Path = args.out

	out_dir.mkdir(parents=True, exist_ok=True)
	cache_path.parent.mkdir(parents=True, exist_ok=True)
	cache = load_cache(cache_path)

	if args.auto_missing:
		products_dir = config.PRODUCTS_FOLDER_PATH
		missing = []
		for product_file in sorted(products_dir.glob("*.json")):
			try:
				with product_file.open("r", encoding="utf-8") as pf:
					data = json.load(pf)
			except Exception:
				continue
			for sku_key, sku_data in data.items():
				if not isinstance(sku_data, dict):
					continue
				if "Images" in sku_data:
					continue
				missing.append(sku_key)

				print(f"\n[{len([s for s in missing if missing.index(sku_key) < missing.index(sku_key) + 1])}/{len(missing)}] Checking {sku_key}...")
				images_dir = find_images_dir_for_sku(sku_key)
				if images_dir:
					process_single_sku(sku_key, images_dir, cache, cache_path, out_dir)
				else:
					print(f"Images folder not found for {sku_key}; searched configured paths")

		print(f"Processed {len(missing)} SKU(s) missing Images")
		return

	# Default single-SKU mode (backward compatible)
	if args.sku and args.images_dir:
		sku = args.sku
		images_dir = Path(args.images_dir)
		process_single_sku(sku, images_dir, cache, cache_path, out_dir)
	else:
		parser.error("sku and images_dir are required unless --auto-missing is used")


if __name__ == "__main__":
	main()
