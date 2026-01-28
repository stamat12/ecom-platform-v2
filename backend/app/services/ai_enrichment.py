"""
AI-powered product details enrichment service.
Uses OpenAI vision to extract and complete product attributes from images.
"""

import os
import json
import base64
import re
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv
from openai import OpenAI

from app.config import ai_config
from app.repositories.sku_json_repo import read_sku_json, _sku_json_path
import config as app_config

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _image_base_dirs() -> List[Path]:
    """Get image base directories from env or config fallback."""
    # Prefer env override for portability
    env_dirs = os.getenv("IMAGE_BASE_DIRS")
    if env_dirs:
        return [Path(p.strip()) for p in env_dirs.split(";") if p.strip()]
    
    # fallback: legacy config - resolve relative to legacy folder
    bases = getattr(app_config, "IMAGE_FOLDER_PATHS", [])
    legacy_dir = Path(app_config.__file__).parent
    resolved = []
    for p in bases:
        path_obj = Path(p)
        if not path_obj.is_absolute():
            # Make relative to legacy folder
            path_obj = (legacy_dir / path_obj).resolve()
        resolved.append(path_obj)
    return resolved


def _image_to_data_uri(image_path: Path) -> str:
    """Convert image file to base64 data URI."""
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    b64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    return f"data:image/*;base64,{b64}"


def _collect_main_image_paths(record: Dict, sku: str) -> tuple[List[Path], str]:
    """
    Collect all main image file paths for a SKU from the JSON record.
    Returns: (list of paths, debug message)
    """
    images_section = record.get("Images", {}) or {}
    main_images = images_section.get("main_images", []) or []
    
    if not main_images:
        return [], f"No main_images array found in Images section for {sku}"

    # Debug: log what we found
    debug_msg = f"Found {len(main_images)} main image(s) in JSON for {sku}"
    
    # Find images folder for this SKU
    image_base_dirs = _image_base_dirs()
    images_dir = None
    for base_dir in image_base_dirs:
        candidate = base_dir / sku
        if candidate.exists() and candidate.is_dir():
            images_dir = candidate
            debug_msg += f"; Found images_dir: {images_dir}"
            break
    
    if not images_dir:
        dirs_checked = [str(d / sku) for d in image_base_dirs]
        return [], f"Could not find images directory for {sku}. Checked: {dirs_checked}"

    # Collect file paths
    filenames: List[str] = []
    for item in main_images:
        if isinstance(item, dict):
            fn = item.get("filename")
            if fn:
                filenames.append(fn)
        elif isinstance(item, str):
            filenames.append(item)

    debug_msg += f"; Extracted {len(filenames)} filenames"

    paths: List[Path] = []
    for fn in filenames:
        p = images_dir / Path(fn).name
        if p.exists():
            paths.append(p)
        else:
            debug_msg += f"; Missing file: {p}"
    
    return paths, debug_msg


def _only_known_keys(d: Dict) -> Dict[str, str]:
    """Filter dict to only include known enrichable fields."""
    return {k: (str(d.get(k)) or "") for k in ai_config.ENRICHABLE_FIELDS}


def _extract_existing_fields(record: Dict) -> Dict[str, str]:
    """Extract current field values from their nested JSON locations."""
    extracted = {k: "" for k in ai_config.ENRICHABLE_FIELDS}
    extracted["Gender"] = record.get("Intern Product Info", {}).get("Gender", "")
    extracted["Brand"] = record.get("Intern Product Info", {}).get("Brand", "")
    extracted["Color"] = record.get("Intern Product Info", {}).get("Color", "")
    extracted["Size"] = record.get("Intern Product Info", {}).get("Size", "")
    extracted["More Details"] = record.get("Intern Generated Info", {}).get("More details", "")
    extracted["Keywords"] = record.get("Intern Generated Info", {}).get("Keywords", "")
    extracted["Materials"] = record.get("Intern Generated Info", {}).get("Materials", "")
    return extracted


def _write_fields_to_record(record: Dict, fields: Dict[str, str]) -> None:
    """Write enriched fields back to their nested JSON locations."""
    if "Intern Product Info" not in record:
        record["Intern Product Info"] = {}
    record["Intern Product Info"]["Gender"] = fields.get("Gender", "")
    record["Intern Product Info"]["Brand"] = fields.get("Brand", "")
    record["Intern Product Info"]["Color"] = fields.get("Color", "")
    record["Intern Product Info"]["Size"] = fields.get("Size", "")
    
    if "Intern Generated Info" not in record:
        record["Intern Generated Info"] = {}
    record["Intern Generated Info"]["More details"] = fields.get("More Details", "")
    record["Intern Generated Info"]["Keywords"] = fields.get("Keywords", "")
    record["Intern Generated Info"]["Materials"] = fields.get("Materials", "")


def normalize_gender_code(value: str) -> str:
    """Map free-text to gender codes: M, F, U, KB, KG, KU."""
    v = (value or "").strip()
    if not v:
        return ""
    vlow = v.lower()

    for token, code in ai_config.GENDER_CODE_MAP.items():
        if token in vlow:
            return code

    if v.upper() in ai_config.VALID_GENDER_CODES:
        return v.upper()

    if any(x in vlow for x in ["universal", "neutral", "one size", "größe-unabhängig", "not gendered"]):
        return ""

    return ""


def _merge_fill_only(existing: Dict[str, str], proposed: Dict[str, str]) -> Dict[str, str]:
    """Merge: only fill empty fields from proposed, keep non-empty existing values."""
    out = dict(existing)
    for k in ai_config.ENRICHABLE_FIELDS:
        if not (out.get(k) or "").strip():
            out[k] = proposed.get(k, "")
    return out


def extract_fields_from_images(image_paths: List[Path], current_fields: Dict[str, str]) -> Dict[str, str]:
    """
    Call OpenAI vision to extract product fields from images.
    Returns enriched fields dict.
    """
    if not image_paths:
        return {k: "" for k in ai_config.ENRICHABLE_FIELDS}

    try:
        content: List[dict] = [
            {
                "type": "text",
                "text": "Aktuelle Felder (fülle nur leere Werte, alles auf Deutsch):\n"
                        + json.dumps(_only_known_keys(current_fields), ensure_ascii=False),
            }
        ]

        # Attach all images as base64 data URIs
        for img_path in image_paths:
            data_uri = _image_to_data_uri(img_path)
            content.append({"type": "image_url", "image_url": {"url": data_uri}})

        response = client.chat.completions.create(
            model=ai_config.OPENAI_MODEL,
            response_format={"type": "json_object"},
            temperature=ai_config.OPENAI_TEMPERATURE,
            max_tokens=ai_config.OPENAI_MAX_TOKENS,
            messages=[
                {"role": "system", "content": ai_config.OPENAI_PROMPT},
                {"role": "user", "content": content},
            ],
        )

        raw = response.choices[0].message.content
        parsed = json.loads(raw)
        cleaned = _only_known_keys(parsed)
        return cleaned

    except Exception as ex:
        print(f"[ERROR] OpenAI vision extraction failed: {ex}")
        return {k: "" for k in ai_config.ENRICHABLE_FIELDS}


def enrich_sku_fields(sku: str) -> Dict[str, any]:
    """
    Enrich product details for a single SKU using OpenAI vision.
    Returns: {"success": bool, "sku": str, "updated_fields": int, "message": str, "data": dict}
    """
    try:
        # Load product JSON
        json_path = _sku_json_path(sku)
        if not json_path or not json_path.exists():
            return {
                "success": False,
                "sku": sku,
                "message": f"Product JSON not found for SKU: {sku}",
            }

        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if sku not in data:
            return {
                "success": False,
                "sku": sku,
                "message": f"SKU {sku} not found in product JSON",
            }

        record = data[sku]

        # Collect main image paths
        image_paths, img_debug = _collect_main_image_paths(record, sku)
        if not image_paths:
            return {
                "success": False,
                "sku": sku,
                "message": f"No main images found for SKU: {sku}. Debug: {img_debug}",
            }

        # Extract current fields
        current_fields = _extract_existing_fields(record)

        # Check if there are empty fields to fill
        empty_fields = {k: v for k, v in current_fields.items() if not (v or "").strip()}
        if not empty_fields:
            return {
                "success": True,
                "sku": sku,
                "updated_fields": 0,
                "message": f"No empty fields to fill for SKU: {sku}",
                "data": current_fields,
            }

        # Extract fields from images using OpenAI
        proposed_fields = extract_fields_from_images(image_paths, current_fields)

        # Merge: only fill empty fields
        merged = _merge_fill_only(current_fields, proposed_fields)

        # Normalize gender code
        if merged.get("Gender"):
            merged["Gender"] = normalize_gender_code(merged["Gender"])

        # Write back to record
        _write_fields_to_record(record, merged)

        # Save updated JSON
        with json_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # Count updated fields
        updated_count = sum(
            1 for k in ai_config.ENRICHABLE_FIELDS 
            if merged.get(k, "").strip() and not (current_fields.get(k, "") or "").strip()
        )

        return {
            "success": True,
            "sku": sku,
            "updated_fields": updated_count,
            "message": f"Successfully enriched {updated_count} field(s) for SKU: {sku}",
            "data": merged,
        }

    except Exception as e:
        return {
            "success": False,
            "sku": sku,
            "message": f"Error enriching SKU {sku}: {str(e)}",
        }


def enrich_multiple_skus(skus: List[str]) -> Dict[str, any]:
    """
    Enrich product details for multiple SKUs.
    Returns: {"success": bool, "total": int, "succeeded": int, "failed": int, "results": {...}}
    """
    results = {}
    succeeded = 0
    failed = 0

    for sku in skus:
        result = enrich_sku_fields(sku)
        results[sku] = result
        if result.get("success"):
            succeeded += 1
        else:
            failed += 1

    return {
        "success": failed == 0,
        "total": len(skus),
        "succeeded": succeeded,
        "failed": failed,
        "results": results,
    }
