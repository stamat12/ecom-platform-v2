"""
OpenAI-powered eBay Item Specifics completion.

Behavior
- Uses all main images for a SKU to infer required and optional eBay aspects.
- Only fills empty fields; existing non-empty values are preserved.
- Writes results into both "eBay Fields" (UI-friendly) and "Ebay" -> "Fields" in the product JSON.
- Returns missing required aspects so the caller can warn the user (Option A).

Public functions
- fill_ebay_fields_for_sku(sku, product_json_path) -> Dict[str, Any]
- fill_ebay_fields_for_skus(list[dict]) -> Dict[str, Any]
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from openai import OpenAI

import config


# ---------------------------------------------------------
# Environment & client
# ---------------------------------------------------------

load_dotenv(dotenv_path=config.PROJECT_ROOT / ".env")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL = config.MODEL_FIELD_COMPLETION  # e.g., "gpt-4o-mini"


# ---------------------------------------------------------
# File & image helpers
# ---------------------------------------------------------

def _atomic_dump(path: Path, payload: dict) -> None:
	tmp = path.with_suffix(".tmp.json")
	with tmp.open("w", encoding="utf-8") as f:
		json.dump(payload, f, ensure_ascii=False, indent=2)
	tmp.replace(path)


def _image_to_data_uri(image_path: Path) -> str:
	if not image_path.exists():
		raise FileNotFoundError(f"Image not found: {image_path}")
	b64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
	return f"data:image/*;base64,{b64}"


def _find_images_dir_for_sku(sku: str) -> Path | None:
	for base in getattr(config, "IMAGE_FOLDER_PATHS", []):
		base_path = base if base.is_absolute() else (config.PROJECT_ROOT / base)
		candidate = base_path / sku
		if candidate.exists() and candidate.is_dir():
			return candidate
	return None


def _collect_main_image_paths(record: Dict[str, Any], sku: str) -> List[Path]:
	images_section = record.get("Images", {}) or {}
	main_images = images_section.get("main_images", []) or []
	if not main_images:
		return []

	images_dir = _find_images_dir_for_sku(sku)
	if not images_dir:
		return []

	filenames: List[str] = []
	for item in main_images:
		if isinstance(item, dict):
			fn = item.get("filename")
			if fn:
				filenames.append(fn)
		elif isinstance(item, str):
			filenames.append(item)

	paths: List[Path] = []
	for fn in filenames:
		p = images_dir / Path(fn).name
		if p.exists():
			paths.append(p)
	return paths


def _load_schema_for_category(category_id: str) -> Dict[str, Any]:
	if not category_id:
		return {}
	schema_filename = f"EbayCat_{category_id}_{config.MARKETPLACE_DE_ID}.json"
	schema_path = config.SCHEMAS_FOLDER_PATH / schema_filename
	if not schema_path.exists():
		return {}
	try:
		with schema_path.open("r", encoding="utf-8") as f:
			data = json.load(f)
		schema = data.get("schema", {}) or {}
		return {
			"required": schema.get("required", []) or [],
			"optional": schema.get("optional", []) or [],
		}
	except Exception:
		return {}


# ---------------------------------------------------------
# Merge helpers
# ---------------------------------------------------------

def _merge_fill_only(existing: Dict[str, str], proposed: Dict[str, str]) -> Dict[str, str]:
	merged = dict(existing)
	for k, v in (proposed or {}).items():
		if not (merged.get(k) or "").strip() and v is not None:
			merged[k] = v
	return merged


def _aspect_names(required_aspects: List[Dict[str, Any]], optional_aspects: List[Dict[str, Any]]) -> List[str]:
	names: List[str] = []
	for aspect in (required_aspects or []) + (optional_aspects or []):
		name = aspect.get("name")
		if name:
			names.append(str(name))
	return names


def _allowed_values_map(aspects: List[Dict[str, Any]]) -> Dict[str, List[str]]:
	out: Dict[str, List[str]] = {}
	for aspect in aspects or []:
		name = aspect.get("name")
		values = aspect.get("values") or []
		if name:
			out[str(name)] = [str(v) for v in values if v]
	return out


# ---------------------------------------------------------
# LLM call
# ---------------------------------------------------------

def _extract_fields_from_images(
	image_paths: List[Path],
	required_aspects: List[Dict[str, Any]],
	optional_aspects: List[Dict[str, Any]],
	current_fields: Dict[str, str],
) -> Dict[str, str]:
	if not image_paths:
		return {}

	field_names = _aspect_names(required_aspects, optional_aspects)
	allowed_map = _allowed_values_map(required_aspects + optional_aspects)

	prompt = (
		"Fülle eBay Item Specifics ausschließlich anhand der bereitgestellten Hauptbilder. "
		f"Gib NUR ein JSON-Objekt mit GENAU diesen Schlüsseln zurück: {field_names}. "
		"Sprache: Deutsch. Keine zusätzlichen Schlüssel, keine Erklärungen.\n"
		"Regeln:\n"
		"- Pflichtfelder dürfen nur leer bleiben, wenn absolut nichts sichtbar oder ableitbar ist.\n"
		"- Optionale Felder: so viele wie möglich befüllen, wenn visuell plausibel.\n"
		"- Wenn erlaubte Werte gegeben sind, wähle nur daraus. Sonst kurze, präzise Beschreibung.\n"
		"- Keine Halluzinationen: wenn unsicher, leeres Feld.\n"
	)

	allowed_snippets = {
		name: values[:15] for name, values in allowed_map.items() if values
	}

	content: List[dict] = [
		{
			"type": "text",
			"text": (
				"Aktuelle Werte (nur leere Felder ergänzen):\n"
				+ json.dumps({k: current_fields.get(k, "") for k in field_names}, ensure_ascii=False)
				+ "\nErlaubte Werte (falls vorhanden):\n"
				+ json.dumps(allowed_snippets, ensure_ascii=False)
			),
		}
	]

	for img_path in image_paths:
		data_uri = _image_to_data_uri(img_path)
		content.append({"type": "image_url", "image_url": {"url": data_uri}})

	try:
		response = client.chat.completions.create(
			model=MODEL,
			response_format={"type": "json_object"},
			temperature=0.1,
			max_tokens=800,
			messages=[
				{"role": "system", "content": prompt},
				{"role": "user", "content": content},
			],
		)
		raw = response.choices[0].message.content
		parsed = json.loads(raw) if raw else {}
		cleaned = {k: str(v) if v is not None else "" for k, v in parsed.items() if k in field_names}
		return cleaned
	except Exception as ex:
		print(f"[ERROR] eBay fields vision extraction failed: {ex}")
		return {}


# ---------------------------------------------------------
# Public API
# ---------------------------------------------------------

def fill_ebay_fields_for_sku(sku: str, product_json_path: Path) -> Dict[str, Any]:
	if not product_json_path.exists():
		raise FileNotFoundError(f"Product JSON not found for {sku}: {product_json_path}")

	with product_json_path.open("r", encoding="utf-8") as f:
		data = json.load(f)

	record = data.get(sku)
	if not isinstance(record, dict):
		raise ValueError(f"Invalid record for {sku}")

	ebay_cat = record.get("Ebay Category", {}) or {}
	category_id = ebay_cat.get("eBay Category ID") if isinstance(ebay_cat, dict) else None
	if not category_id:
		raise ValueError("Missing eBay Category ID")

	schema = _load_schema_for_category(str(category_id))
	required_aspects = schema.get("required", []) if schema else []
	optional_aspects = schema.get("optional", []) if schema else []
	if not required_aspects and not optional_aspects:
		raise ValueError(f"No schema found for category {category_id}")

	# Get current fields from structured format
	existing_ebay_fields = record.get("eBay Fields", {}) or {}
	current_required = existing_ebay_fields.get("required", {}) if isinstance(existing_ebay_fields, dict) else {}
	current_optional = existing_ebay_fields.get("optional", {}) if isinstance(existing_ebay_fields, dict) else {}
	# Flatten for processing
	current_fields = {**current_required, **current_optional}

	image_paths = _collect_main_image_paths(record, sku)
	if not image_paths:
		raise ValueError(f"No main images found for {sku}")

	proposed = _extract_fields_from_images(image_paths, required_aspects, optional_aspects, current_fields)
	merged = _merge_fill_only(current_fields, proposed)

	# Split merged fields back into required/optional
	required_names = {aspect.get("name") for aspect in required_aspects if aspect.get("name")}
	merged_required = {k: v for k, v in merged.items() if k in required_names}
	merged_optional = {k: v for k, v in merged.items() if k not in required_names}

	# Compute missing required after merge
	missing_required = [
		name for name in required_names
		if not (merged_required.get(name) or "").strip()
	]

	# Write back in structured format (single eBay Fields section with required/optional)
	record["eBay Fields"] = {
		"required": merged_required,
		"optional": merged_optional
	}
	
	# Remove legacy Ebay section if it exists
	if "Ebay" in record and "Fields" in record.get("Ebay", {}):
		del record["Ebay"]

	data[sku] = record
	_atomic_dump(product_json_path, data)

	return {
		"fields": merged,
		"required_fields": merged_required,
		"optional_fields": merged_optional,
		"missing_required": list(missing_required),
		"used_images": len(image_paths),
	}