from __future__ import annotations

import logging
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.repositories.sku_json_repo import read_sku_json, write_sku_json
from app.services.image_listing import _find_sku_dir
from app.config.ai_config import PROMPTS

logger = logging.getLogger(__name__)


# === External ecommerceAI integration ===

def _get_ecommerce_ai_root() -> Path:
    return Path(__file__).resolve().parents[4] / "ecommerceAI"


def _add_ecommerce_ai_to_syspath() -> None:
    ecommerce_ai_root = _get_ecommerce_ai_root()
    if str(ecommerce_ai_root) not in sys.path:
        sys.path.insert(0, str(ecommerce_ai_root))


def _load_prompts() -> Dict[str, str]:
    _add_ecommerce_ai_to_syspath()
    try:
        # Use local config from this project
        return PROMPTS
    except Exception as exc:
        logger.error("Failed to load prompts: %s", exc)
        return {}


def list_enhance_prompts() -> List[Dict[str, str]]:
    prompts = _load_prompts()
    return [
        {"key": key, "label": key.replace("_", " ").title()}
        for key in prompts.keys()
    ]


# === JSON helpers ===

def _ensure_images_section(product_json: Dict[str, Any]) -> Dict[str, Any]:
    images_section = product_json.get("Images", {}) if isinstance(product_json.get("Images"), dict) else {}
    if not isinstance(images_section, dict):
        images_section = {}

    images_section.setdefault("schema_version", "1.0")
    images_section.setdefault("stock", [])
    images_section.setdefault("phone", [])
    images_section.setdefault("enhanced", [])
    images_section.setdefault("summary", {})
    return images_section


def _update_images_summary(images_section: Dict[str, Any]) -> None:
    stock = list(images_section.get("stock", []) or [])
    phone = list(images_section.get("phone", []) or [])
    enhanced = list(images_section.get("enhanced", []) or [])

    images_section["summary"] = {
        "has_stock": bool(stock),
        "has_phone": bool(phone),
        "has_enhanced": bool(enhanced),
        "count_stock": len(stock),
        "count_phone": len(phone),
        "count_enhanced": len(enhanced),
    }


# === Enhance (AI) ===

def enhance_images_for_sku(
    sku: str,
    filenames: List[str],
    prompt_key: str,
) -> Dict[str, Any]:
    _add_ecommerce_ai_to_syspath()
    from agents.image_generator import generate_enhanced_image  # type: ignore

    prompts = _load_prompts()
    prompt_text = prompts.get(prompt_key)
    if not prompt_text:
        return {
            "success": False,
            "message": f"Unknown prompt key: {prompt_key}",
            "sku": sku,
            "prompt_key": prompt_key,
            "processed_count": 0,
            "generated": [],
            "errors": [f"Unknown prompt key: {prompt_key}"],
        }

    sku_dir = _find_sku_dir(sku)
    if not sku_dir:
        return {
            "success": False,
            "message": f"Images folder not found for SKU {sku}",
            "sku": sku,
            "prompt_key": prompt_key,
            "processed_count": 0,
            "generated": [],
            "errors": [f"Images folder not found for SKU {sku}"]
        }

    product_json = read_sku_json(sku) or {}
    images_section = _ensure_images_section(product_json)
    enhanced = list(images_section.get("enhanced", []) or [])
    existing = {e.get("filename") for e in enhanced if isinstance(e, dict)}

    generated: List[str] = []
    errors: List[str] = []

    for filename in filenames:
        source_path = sku_dir / filename
        if not source_path.exists():
            errors.append(f"{filename}: file not found")
            continue

        output_path, error = generate_enhanced_image(
            source_path, prompt_key, prompt_text, output_dir=sku_dir
        )
        if error:
            errors.append(f"{filename}: {error}")
            continue

        if output_path and output_path.name not in existing:
            enhanced.append({
                "filename": output_path.name,
                "source": filename,
                "prompt": prompt_key,
                "generated": True,
            })
            existing.add(output_path.name)

        if output_path:
            generated.append(output_path.name)

    images_section["enhanced"] = enhanced
    _update_images_summary(images_section)
    product_json["Images"] = images_section
    write_sku_json(sku, product_json)

    return {
        "success": len(generated) > 0,
        "message": "Enhanced images generated" if generated else "No images generated",
        "sku": sku,
        "prompt_key": prompt_key,
        "processed_count": len(generated),
        "generated": generated,
        "errors": errors,
    }


def enhance_images_batch(
    images: List[Dict[str, str]],
    prompt_key: str,
) -> Dict[str, Any]:
    sku_groups: Dict[str, List[str]] = defaultdict(list)
    for img in images:
        sku = img.get("sku")
        filename = img.get("filename")
        if sku and filename:
            sku_groups[sku].append(filename)

    results = []
    processed_count = 0
    errors = 0

    for sku, filenames in sku_groups.items():
        result = enhance_images_for_sku(sku, filenames, prompt_key)
        processed_count += result.get("processed_count", 0)
        sku_errors = result.get("errors", []) or []
        if sku_errors:
            errors += len(sku_errors)
            for err in sku_errors:
                results.append({"sku": sku, "filename": "", "success": False, "error": err})
        for gen in result.get("generated", []) or []:
            results.append({"sku": sku, "filename": gen, "success": True, "error": None})

    return {
        "success": processed_count > 0 and errors == 0,
        "message": "Batch enhancement completed",
        "processed_count": processed_count,
        "prompt_key": prompt_key,
        "results": results,
    }


# === Upscale ===

def upscale_images_for_sku(sku: str, filenames: List[str], scale: int = 4) -> Dict[str, Any]:
    _add_ecommerce_ai_to_syspath()
    from agents.image_upscaler import upscale_image  # type: ignore

    sku_dir = _find_sku_dir(sku)
    if not sku_dir:
        return {
            "success": False,
            "message": f"Images folder not found for SKU {sku}",
            "sku": sku,
            "processed_count": 0,
            "upscaled": [],
            "errors": [f"Images folder not found for SKU {sku}"]
        }

    product_json = read_sku_json(sku) or {}
    images_section = _ensure_images_section(product_json)
    enhanced = list(images_section.get("enhanced", []) or [])
    enhanced_by_filename = {
        e.get("filename"): e for e in enhanced if isinstance(e, dict) and e.get("filename")
    }

    upscaled: List[str] = []
    errors: List[str] = []

    for filename in filenames:
        source_path = sku_dir / filename
        if not source_path.exists():
            errors.append(f"{filename}: file not found")
            continue

        output_path, error = upscale_image(source_path, output_dir=sku_dir, scale=scale)
        if error:
            errors.append(f"{filename}: {error}")
            continue

        if not output_path:
            errors.append(f"{filename}: upscale failed")
            continue

        new_name = output_path.name
        if filename in enhanced_by_filename:
            entry = enhanced_by_filename[filename]
            entry["filename"] = new_name
            entry["upscaled"] = True
            entry["scale"] = scale
        else:
            enhanced.append({
                "filename": new_name,
                "source": filename,
                "upscaled": True,
                "scale": scale,
            })

        upscaled.append(new_name)

        try:
            if source_path.exists():
                source_path.unlink()
        except Exception:
            pass

    images_section["enhanced"] = enhanced
    _update_images_summary(images_section)
    product_json["Images"] = images_section
    write_sku_json(sku, product_json)

    return {
        "success": len(upscaled) > 0,
        "message": "Upscaling completed" if upscaled else "No images upscaled",
        "sku": sku,
        "processed_count": len(upscaled),
        "upscaled": upscaled,
        "errors": errors,
    }


def upscale_images_batch(images: List[Dict[str, str]], scale: int = 4) -> Dict[str, Any]:
    sku_groups: Dict[str, List[str]] = defaultdict(list)
    for img in images:
        sku = img.get("sku")
        filename = img.get("filename")
        if sku and filename:
            sku_groups[sku].append(filename)

    results = []
    processed_count = 0
    errors = 0

    for sku, filenames in sku_groups.items():
        result = upscale_images_for_sku(sku, filenames, scale=scale)
        processed_count += result.get("processed_count", 0)
        sku_errors = result.get("errors", []) or []
        if sku_errors:
            errors += len(sku_errors)
            for err in sku_errors:
                results.append({"sku": sku, "filename": "", "success": False, "error": err})
        for up in result.get("upscaled", []) or []:
            results.append({"sku": sku, "filename": up, "success": True, "error": None})

    return {
        "success": processed_count > 0 and errors == 0,
        "message": "Batch upscaling completed",
        "processed_count": processed_count,
        "results": results,
    }
