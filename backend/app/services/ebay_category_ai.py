from __future__ import annotations

import base64
import json
import logging
import re
import sqlite3
import unicodedata
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from app.config.ebay_config import EBAY_ENRICHMENT_MODEL
from app.repositories.sku_json_repo import read_sku_json, write_sku_json
from app.services.ebay_enrichment import get_openai_client
from app.services.excel_inventory import _get_db_path
from app.services.image_listing import list_images_for_sku

logger = logging.getLogger(__name__)

_category_debug_logger: Optional[logging.Logger] = None
_category_token_idf_cache: Optional[Dict[str, float]] = None
_GENERIC_TOKENS = {
	"zubehor",
	"zubehoer",
	"accessoires",
	"sonstige",
	"weitere",
	"artikel",
	"sets",
}
_STOPWORDS = {
	"fur",
	"mit",
	"und",
	"oder",
	"der",
	"die",
	"das",
	"dem",
	"den",
	"des",
	"ein",
	"eine",
	"einer",
	"eines",
	"ist",
	"sind",
	"von",
	"vom",
	"zur",
	"zum",
	"bei",
	"im",
	"am",
	"an",
	"in",
	"auf",
	"off",
	"for",
	"with",
	"and",
	"the",
	"this",
	"that",
	"these",
	"those",
	"from",
	"into",
	"your",
	"our",
	"you",
	"are",
	"cm",
	"mm",
	"xl",
	"xxl",
	"set",
	"pack",
	"pcs",
}


def _get_category_debug_logger() -> logging.Logger:
	global _category_debug_logger
	if _category_debug_logger is not None:
		return _category_debug_logger

	debug_logger = logging.getLogger("ebay_category_ai_debug")
	debug_logger.setLevel(logging.INFO)
	debug_logger.propagate = False

	logs_dir = Path(__file__).resolve().parents[2] / "logs"
	logs_dir.mkdir(parents=True, exist_ok=True)
	log_file = logs_dir / "ebay_category_ai.log"

	existing = [
		h
		for h in debug_logger.handlers
		if isinstance(h, logging.FileHandler)
		and Path(getattr(h, "baseFilename", "")).resolve() == log_file.resolve()
	]
	if not existing:
		handler = logging.FileHandler(log_file, encoding="utf-8")
		handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
		debug_logger.addHandler(handler)

	_category_debug_logger = debug_logger
	return _category_debug_logger


def _category_log(event: str, trace_id: str, **fields: Any) -> None:
	payload = {
		"event": event,
		"trace_id": trace_id,
		"ts": datetime.utcnow().isoformat(timespec="seconds") + "Z",
	}
	payload.update(fields)
	try:
		_get_category_debug_logger().info(json.dumps(payload, ensure_ascii=False, default=str))
	except Exception as e:
		logger.warning(f"Failed to write category debug log ({event}): {e}")


def _pick_column(columns: List[str], keywords: List[str]) -> Optional[str]:
	lowered = {c: c.lower() for c in columns}
	for keyword in keywords:
		for col, col_lower in lowered.items():
			if keyword in col_lower:
				return col
	return None


def _normalize_category_path(raw_path: str) -> str:
	parts = [p.strip() for p in str(raw_path or "").split("/") if str(p).strip()]
	return "/" + "/".join(parts) if parts else ""


def _path_parts(path: str) -> List[str]:
	return [p.strip() for p in str(path or "").split("/") if str(p).strip()]


def _normalize_text(value: Any) -> str:
	text = str(value or "").strip().lower()
	if not text:
		return ""
	text = text.replace("ß", "ss")
	text = unicodedata.normalize("NFKD", text)
	text = "".join(ch for ch in text if not unicodedata.combining(ch))
	return text


def _tokenize(value: Any) -> List[str]:
	text = _normalize_text(value)
	if not text:
		return []
	out: List[str] = []
	for raw in re.findall(r"[a-z0-9]{2,}", text):
		token = raw
		if len(token) > 4 and token.endswith("s"):
			token = token[:-1]
		if len(token) > 5 and token.endswith("en"):
			token = token[:-2]
		if len(token) > 5 and token.endswith("er"):
			token = token[:-2]
		if len(token) < 3:
			continue
		if token in _STOPWORDS:
			continue
		out.append(token)
	return out


def _build_category_token_idf(entries: List[Dict[str, Any]]) -> Dict[str, float]:
	global _category_token_idf_cache
	if _category_token_idf_cache is not None:
		return _category_token_idf_cache

	n = max(len(entries), 1)
	doc_freq: Dict[str, int] = {}
	for entry in entries:
		unique_tokens = set(entry.get("tokens") or [])
		for token in unique_tokens:
			doc_freq[token] = doc_freq.get(token, 0) + 1

	idf: Dict[str, float] = {}
	for token, df in doc_freq.items():
		idf[token] = 1.0 + math.log((n + 1) / (df + 1))

	_category_token_idf_cache = idf
	return idf


def _load_category_entries() -> List[Dict[str, Any]]:
	db_path = _get_db_path()
	conn = sqlite3.connect(db_path)
	conn.row_factory = sqlite3.Row
	try:
		columns = [r[1] for r in conn.execute("PRAGMA table_info(ebay_categories)").fetchall()]
		if not columns:
			return []

		id_col = _pick_column(columns, ["id"])
		path_col = _pick_column(columns, ["path", "full"])
		name_col = _pick_column(columns, ["name", "category"])

		rows = conn.execute("SELECT * FROM ebay_categories").fetchall()
		entries: List[Dict[str, Any]] = []
		seen = set()

		for row in rows:
			row_dict = dict(row)
			category_id = str(row_dict.get(id_col, "") or "").strip() if id_col else ""
			raw_path = row_dict.get(path_col) if path_col else None
			if not raw_path:
				raw_path = row_dict.get(name_col) if name_col else ""

			category_path = _normalize_category_path(str(raw_path or ""))
			if not category_path:
				continue

			parts = _path_parts(category_path)
			if not parts:
				continue

			dedupe_key = (category_path.lower(), category_id)
			if dedupe_key in seen:
				continue
			seen.add(dedupe_key)

			entries.append(
				{
					"category_id": category_id,
					"category_path": category_path,
					"parts": parts,
					"tokens": _tokenize(" ".join(parts)),
				}
			)

		return entries
	finally:
		conn.close()


def _collect_main_image_paths(sku: str, product_json: Dict[str, Any], max_images: int = 2) -> List[Path]:
	images_section = product_json.get("Images", {}) or {}
	main_images = images_section.get("main_images", []) or []
	main_filenames: List[str] = []
	for item in main_images:
		if isinstance(item, dict) and item.get("filename"):
			main_filenames.append(str(item["filename"]))
		elif isinstance(item, str):
			main_filenames.append(item)

	if not main_filenames:
		return []

	all_images_info = list_images_for_sku(sku)
	by_name = {
		str(img.get("filename", "")).strip().lower(): img
		for img in (all_images_info.get("images") or [])
		if isinstance(img, dict)
	}

	paths: List[Path] = []
	for fn in main_filenames:
		info = by_name.get(Path(fn).name.lower())
		if not info:
			continue
		full_path = str(info.get("full_path") or "").strip()
		if not full_path:
			continue
		p = Path(full_path)
		if p.exists() and p.is_file():
			paths.append(p)
		if len(paths) >= max_images:
			break

	return paths


def _image_to_data_uri(image_path: Path) -> str:
	b64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
	return f"data:image/*;base64,{b64}"


def _build_product_context(sku: str, product_json: Dict[str, Any]) -> Dict[str, Any]:
	intern_info = product_json.get("Intern Product Info", {}) if isinstance(product_json.get("Intern Product Info"), dict) else {}
	intern_generated = product_json.get("Intern Generated Info", {}) if isinstance(product_json.get("Intern Generated Info"), dict) else {}
	supplier_data = product_json.get("Supplier Data", {}) if isinstance(product_json.get("Supplier Data"), dict) else {}
	condition_data = product_json.get("Product Condition", {}) if isinstance(product_json.get("Product Condition"), dict) else {}
	ebay_seo = product_json.get("eBay SEO", {}) if isinstance(product_json.get("eBay SEO"), dict) else {}

	return {
		"sku": sku,
		"supplier_title": supplier_data.get("Supplier Title", ""),
		"brand": intern_info.get("Brand", ""),
		"gender": intern_info.get("Gender", ""),
		"color": intern_info.get("Color", ""),
		"size": intern_info.get("Size", ""),
		"keywords": intern_generated.get("Keywords", ""),
		"more_details": intern_generated.get("More details", ""),
		"materials": intern_generated.get("Materials", ""),
		"condition": condition_data.get("Condition", ""),
		"seo_product_type": ebay_seo.get("Product Type", ""),
		"seo_model": ebay_seo.get("Product Model", ""),
		"seo_keyword_1": ebay_seo.get("Keyword 1", ""),
		"seo_keyword_2": ebay_seo.get("Keyword 2", ""),
		"seo_keyword_3": ebay_seo.get("Keyword 3", ""),
	}


def _build_weighted_context_tokens(context: Dict[str, Any]) -> Dict[str, float]:
	field_weights = {
		"supplier_title": 3.0,
		"seo_product_type": 3.0,
		"keywords": 2.5,
		"seo_keyword_1": 2.2,
		"seo_keyword_2": 2.0,
		"seo_keyword_3": 1.8,
		"more_details": 1.3,
		"brand": 1.5,
		"seo_model": 1.5,
		"materials": 1.0,
		"color": 0.8,
		"size": 0.6,
		"gender": 0.6,
		"condition": 0.4,
	}
	token_scores: Dict[str, float] = {}

	for field, weight in field_weights.items():
		for token in _tokenize(context.get(field, "")):
			token_scores[token] = token_scores.get(token, 0.0) + weight

	return token_scores


def _root_domain_adjustment(parts: List[str], context_text: str) -> float:
	if not parts:
		return 0.0
	root = _normalize_text(parts[0])

	industrial_signals = ["industrie", "gewerbe", "gastro", "werkstatt", "ersatzteil", "maschinen"]
	collectible_signals = ["sammler", "collectible", "vintage", "antik", "memorabilia", "raritat"]

	has_industrial_signal = any(token in context_text for token in industrial_signals)
	has_collectible_signal = any(token in context_text for token in collectible_signals)

	if "business" in root or "industrie" in root:
		return 0.0 if has_industrial_signal else -2.2
	if "sammeln" in root or "selten" in root:
		return 0.0 if has_collectible_signal else -2.4
	return 0.0


def _score_category_entry(
	entry: Dict[str, Any],
	token_scores: Dict[str, float],
	idf_map: Dict[str, float],
	context_text: str,
) -> float:
	parts = entry.get("parts") or []
	tokens = entry.get("tokens") or []
	if not parts or not tokens:
		return 0.0

	score = 0.0
	depth = len(parts)
	for token in tokens:
		weight = token_scores.get(token, 0.0)
		if weight <= 0:
			continue
		token_boost = 1.0
		if token in _GENERIC_TOKENS:
			token_boost = 0.35
		idf = idf_map.get(token, 1.0)
		score += weight * token_boost * idf

	# Slight preference for deeper paths when the textual match is similar.
	score += min(depth, 6) * 0.08
	score += _root_domain_adjustment(parts, context_text)
	return score


def _normalize_ai_choice(raw_choice: str, options: List[str]) -> Optional[str]:
	if not raw_choice:
		return None
	cleaned = str(raw_choice).strip()
	if cleaned in options:
		return cleaned

	lowered_map = {opt.lower(): opt for opt in options}
	if cleaned.lower() in lowered_map:
		return lowered_map[cleaned.lower()]

	for opt in options:
		if cleaned.lower() in opt.lower() or opt.lower() in cleaned.lower():
			return opt
	return None


def _ai_rerank_category_paths(
	options: List[str],
	context: Dict[str, Any],
	image_paths: List[Path],
	trace_id: str,
	sku: str,
) -> Optional[str]:
	if not options:
		return None
	if len(options) == 1:
		return options[0]

	try:
		_category_log(
			"category_ai_rerank_request",
			trace_id,
			sku=sku,
			options_count=len(options),
			options_preview=options[:12],
			use_images=bool(image_paths),
			image_count=len(image_paths),
		)

		client = get_openai_client()
		content: List[Dict[str, Any]] = [
			{
				"type": "text",
				"text": (
					"Du wählst die beste eBay-Kategorie aus einer vorgefilterten Liste. "
					"Regel: bewerte primär die PRODUKTART/FUNKTION (was ist das Produkt), "
					"nicht den Nutzungsort. Wähle GENAU einen exakten Kategorienpfad aus den Optionen. "
					"Antworte NUR als JSON: "
					'{"choice":"<exakter Kategorienpfad>","reason":"kurz"}.\n\n'
					f"Optionen: {json.dumps(options, ensure_ascii=False)}\n"
					f"Produktkontext: {json.dumps(context, ensure_ascii=False)}"
				),
			}
		]

		for img_path in image_paths:
			try:
				content.append({"type": "image_url", "image_url": {"url": _image_to_data_uri(img_path)}})
			except Exception as e:
				logger.warning(f"Failed to attach image for category AI rerank ({img_path}): {e}")

		response = client.chat.completions.create(
			model=EBAY_ENRICHMENT_MODEL,
			response_format={"type": "json_object"},
			temperature=0,
			max_tokens=220,
			messages=[
				{"role": "system", "content": "Du bist ein präziser eBay-Kategorisierer."},
				{"role": "user", "content": content},
			],
		)

		raw = response.choices[0].message.content
		if not raw:
			_category_log("category_ai_rerank_empty_response", trace_id, sku=sku)
			return None

		parsed = json.loads(raw)
		choice = _normalize_ai_choice(str(parsed.get("choice") or ""), options)
		_category_log(
			"category_ai_rerank_response",
			trace_id,
			sku=sku,
			raw_choice=str(parsed.get("choice") or ""),
			normalized_choice=choice or "",
			reason=str(parsed.get("reason") or ""),
		)
		return choice
	except Exception as e:
		logger.warning(f"Category AI rerank failed: {e}")
		_category_log("category_ai_rerank_error", trace_id, sku=sku, error=str(e))
		return None


def _rank_category_candidates(entries: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Tuple[float, Dict[str, Any]]]:
	token_scores = _build_weighted_context_tokens(context)
	idf_map = _build_category_token_idf(entries)
	context_text = _normalize_text(" ".join(str(v or "") for v in context.values()))
	ranked: List[Tuple[float, Dict[str, Any]]] = []
	for entry in entries:
		ranked.append((_score_category_entry(entry, token_scores, idf_map, context_text), entry))
	ranked.sort(key=lambda x: (-x[0], x[1]["category_path"]))
	return ranked


def _save_selected_category(sku: str, product_json: Dict[str, Any], chosen: Dict[str, Any]) -> None:
	if "Ebay Category" not in product_json or not isinstance(product_json.get("Ebay Category"), dict):
		product_json["Ebay Category"] = {}

	product_json["Ebay Category"]["Category"] = chosen["category_path"]
	if chosen.get("category_id"):
		product_json["Ebay Category"]["eBay Category ID"] = str(chosen["category_id"])

	write_sku_json(sku, product_json)


def detect_and_save_ebay_category_for_sku(sku: str, use_images: bool = True) -> Dict[str, Any]:
	trace_id = uuid4().hex[:12]
	_category_log("category_detect_start", trace_id, sku=sku, use_images=use_images)

	product_json = read_sku_json(sku)
	if not product_json:
		_category_log("category_detect_no_json", trace_id, sku=sku)
		return {"success": False, "sku": sku, "message": f"No JSON found for SKU {sku}"}

	entries = _load_category_entries()
	if not entries:
		_category_log("category_detect_no_categories", trace_id, sku=sku)
		return {"success": False, "sku": sku, "message": "No eBay categories found in database"}

	context = _build_product_context(sku, product_json)
	image_paths = _collect_main_image_paths(sku, product_json, max_images=2) if use_images else []
	_category_log(
		"category_detect_context_loaded",
		trace_id,
		sku=sku,
		category_count=len(entries),
		image_count=len(image_paths),
		context_preview={
			"supplier_title": context.get("supplier_title", ""),
			"brand": context.get("brand", ""),
			"keywords": context.get("keywords", ""),
			"more_details": str(context.get("more_details", ""))[:240],
		},
	)

	ranked = _rank_category_candidates(entries, context)
	if not ranked:
		_category_log("category_detect_no_ranked_candidates", trace_id, sku=sku)
		return {"success": False, "sku": sku, "message": "Could not rank categories"}

	shortlist_size = 20
	ai_pool_size = 10
	shortlist = ranked[:shortlist_size]
	top_score = shortlist[0][0]
	second_score = shortlist[1][0] if len(shortlist) > 1 else 0.0
	confidence_margin = top_score - second_score

	_category_log(
		"category_detect_ranked",
		trace_id,
		sku=sku,
		top_score=round(top_score, 4),
		second_score=round(second_score, 4),
		confidence_margin=round(confidence_margin, 4),
		shortlist_count=len(shortlist),
		top_paths=[s[1]["category_path"] for s in shortlist[:8]],
	)

	chosen_entry: Optional[Dict[str, Any]] = None
	source = "deterministic"

	# High-confidence deterministic pick: avoids unnecessary AI drift.
	if top_score >= 3.0 and confidence_margin >= 1.2:
		chosen_entry = shortlist[0][1]
	else:
		ai_options = [item[1]["category_path"] for item in shortlist[:ai_pool_size]]
		ai_choice = _ai_rerank_category_paths(ai_options, context, image_paths, trace_id, sku)
		if ai_choice:
			for _, candidate in shortlist:
				if candidate["category_path"] == ai_choice:
					chosen_entry = candidate
					source = "ai_rerank"
					break

	if chosen_entry is None:
		chosen_entry = shortlist[0][1]
		source = "fallback_top_rank"

	_save_selected_category(sku, product_json, chosen_entry)
	selected_levels = chosen_entry.get("parts") or _path_parts(chosen_entry.get("category_path", ""))

	_category_log(
		"category_detect_saved",
		trace_id,
		sku=sku,
		category_path=chosen_entry["category_path"],
		category_id=str(chosen_entry.get("category_id") or ""),
		selected_levels=selected_levels,
		source=source,
		used_images=len(image_paths),
	)

	return {
		"success": True,
		"sku": sku,
		"category_path": chosen_entry["category_path"],
		"category_id": str(chosen_entry.get("category_id") or ""),
		"selected_levels": selected_levels,
		"source": source,
		"used_images": len(image_paths),
	}


def detect_and_save_ebay_category_for_skus(skus: List[str], use_images: bool = True) -> Dict[str, Any]:
	batch_trace_id = uuid4().hex[:12]
	_category_log("category_detect_batch_start", batch_trace_id, total=len(skus), use_images=use_images, skus=skus)

	results = []
	succeeded = 0
	failed = 0

	for sku in skus:
		result = detect_and_save_ebay_category_for_sku(sku, use_images=use_images)
		results.append(result)
		if result.get("success"):
			succeeded += 1
		else:
			failed += 1

	_category_log(
		"category_detect_batch_complete",
		batch_trace_id,
		total=len(skus),
		succeeded=succeeded,
		failed=failed,
	)

	return {
		"success": failed == 0,
		"total": len(skus),
		"succeeded": succeeded,
		"failed": failed,
		"results": results,
	}
