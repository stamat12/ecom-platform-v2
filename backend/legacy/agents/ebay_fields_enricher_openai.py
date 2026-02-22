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

SEO_FIELD_KEYS = ["product_type", "product_model", "keyword_1", "keyword_2", "keyword_3"]

_DEFAULT_SEO_ENRICHMENT_PROMPT = """
You are an expert eBay Germany product classifier.

Your task is to analyze product titles and extract:

- product_type
- product_model
- keyword_1
- keyword_2
- keyword_3

Your goal is to maximize search visibility on eBay.de using realistic buyer search terms.

You MUST follow these strict rules:

OUTPUT FORMAT:

- Output ONLY valid JSON.
- Output exactly these 5 fields:
	product_type, product_model, keyword_1, keyword_2, keyword_3
- All output must be in German.
- Use singular form for product_type.
- Capitalize nouns properly.

PRODUCT TYPE RULES:

- product_type must be the main item category.
- Choose the most specific product type possible.
- Do NOT include brand names.
- Do NOT include color.
- Do NOT include size.
- Do NOT include condition words like Neu or Gebraucht.

PRODUCT MODEL RULES:

- product_model should be the most likely model designation from title (if available).
- If no clear model is present, return empty string.
- Do NOT include color, size, or condition.

KEYWORD RULES:

- keyword_1, keyword_2, keyword_3 must be alternative search terms.
- They must describe the same product.
- Use realistic eBay search keywords.
- Do NOT include brand names.
- Do NOT include colors.
- Do NOT include sizes.
- Do NOT include condition.

IMPORTANT:

- Keywords must help buyers find the product.
- Do NOT repeat product_type as keyword unless absolutely necessary.
- Choose the most likely product type based on the title.

Always output valid JSON only.
""".strip()


def _load_enrichment_prompts() -> dict:
	prompts_path = config.PROJECT_ROOT.parent / "data" / "enrichment_prompts.json"
	try:
		with prompts_path.open("r", encoding="utf-8") as f:
			loaded = json.load(f)
		return loaded if isinstance(loaded, dict) else {}
	except Exception:
		return {}


_LOADED_ENRICHMENT_PROMPTS = _load_enrichment_prompts()
_RAW_SEO_PROMPT = _LOADED_ENRICHMENT_PROMPTS.get("ebay_seo_enrichment_prompt")
if isinstance(_RAW_SEO_PROMPT, list):
	SEO_ENRICHMENT_PROMPT = "\n".join(str(line) for line in _RAW_SEO_PROMPT)
elif isinstance(_RAW_SEO_PROMPT, str):
	SEO_ENRICHMENT_PROMPT = _RAW_SEO_PROMPT
else:
	SEO_ENRICHMENT_PROMPT = _DEFAULT_SEO_ENRICHMENT_PROMPT


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


def _extract_title_for_seo(record: Dict[str, Any], sku: str) -> str:
	candidates: List[str] = []

	def _push(value: Any) -> None:
		if value is None:
			return
		text = str(value).strip()
		if text:
			candidates.append(text)

	for key in ["Title", "Product Title", "Titel", "Name", "Product Name", "eBay Title", "Ebay Title"]:
		_push(record.get(key))

	intern_product = record.get("Intern Product Info", {})
	if isinstance(intern_product, dict):
		for key in ["Title", "Product Title", "Titel", "Name", "Model", "Product Name"]:
			_push(intern_product.get(key))

	intern_generated = record.get("Intern Generated Info", {})
	if isinstance(intern_generated, dict):
		for key in ["Title", "Product Title", "Titel", "Name", "SEO Title", "Keywords"]:
			_push(intern_generated.get(key))

	ebay_listing = record.get("Ebay Listing", {})
	if isinstance(ebay_listing, dict):
		for key in ["Title", "Listing Title", "eBay Title", "Ebay Title"]:
			_push(ebay_listing.get(key))

	if candidates:
		return candidates[0]

	raise ValueError(f"No product title found for {sku}")


def _extract_seo_from_title(title: str) -> Dict[str, str]:
	try:
		response = client.chat.completions.create(
			model=MODEL,
			response_format={"type": "json_object"},
			temperature=0.1,
			max_tokens=300,
			messages=[
				{"role": "system", "content": SEO_ENRICHMENT_PROMPT},
				{
					"role": "user",
					"content": (
						"Produkt-Titel:\n"
						f"{title}\n\n"
						"Liefere ausschließlich JSON mit genau diesen Keys: "
						"product_type, product_model, keyword_1, keyword_2, keyword_3"
					),
				},
			],
		)
		raw = response.choices[0].message.content
		parsed = json.loads(raw) if raw else {}
		return {
			"product_type": str(parsed.get("product_type") or "").strip(),
			"product_model": str(parsed.get("product_model") or "").strip(),
			"keyword_1": str(parsed.get("keyword_1") or "").strip(),
			"keyword_2": str(parsed.get("keyword_2") or "").strip(),
			"keyword_3": str(parsed.get("keyword_3") or "").strip(),
		}
	except Exception as ex:
		print(f"[ERROR] eBay SEO extraction failed: {ex}")
		return {k: "" for k in SEO_FIELD_KEYS}


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

	# Enrich SEO fields from title (fill only empty values)
	existing_seo = record.get("eBay SEO", {}) if isinstance(record.get("eBay SEO", {}), dict) else {}
	current_seo = {
		"product_type": str(existing_seo.get("Product Type") or "").strip(),
		"product_model": str(existing_seo.get("Product Model") or "").strip(),
		"keyword_1": str(existing_seo.get("Keyword 1") or "").strip(),
		"keyword_2": str(existing_seo.get("Keyword 2") or "").strip(),
		"keyword_3": str(existing_seo.get("Keyword 3") or "").strip(),
	}
	title = _extract_title_for_seo(record, sku)
	proposed_seo = _extract_seo_from_title(title)
	for key in SEO_FIELD_KEYS:
		if not current_seo.get(key) and proposed_seo.get(key):
			current_seo[key] = proposed_seo[key]

	record["eBay SEO"] = {
		"Product Type": current_seo.get("product_type", ""),
		"Product Model": current_seo.get("product_model", ""),
		"Keyword 1": current_seo.get("keyword_1", ""),
		"Keyword 2": current_seo.get("keyword_2", ""),
		"Keyword 3": current_seo.get("keyword_3", ""),
	}

	data[sku] = record
	_atomic_dump(product_json_path, data)

	return {
		"fields": merged,
		"required_fields": merged_required,
		"optional_fields": merged_optional,
		"missing_required": list(missing_required),
		"used_images": len(image_paths),
		"seo_fields": current_seo,
	}