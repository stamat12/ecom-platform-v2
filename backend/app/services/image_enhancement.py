from __future__ import annotations

import json
import logging
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

from PIL import Image

from app.repositories.sku_json_repo import read_sku_json, write_sku_json
from app.services.image_listing import _find_sku_dir

logger = logging.getLogger(__name__)


# === Legacy config integration ===

LEGACY = Path(__file__).resolve().parents[2] / "legacy"
if str(LEGACY) not in sys.path:
    sys.path.insert(0, str(LEGACY))
import config  # type: ignore


def _prompts_file_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "prompts.json"


def _load_prompts_from_file() -> List[Dict[str, str]]:
    path = _prompts_file_path()
    if not path.exists():
        return []

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.error("Failed to read prompts JSON: %s", exc)
        return []

    if isinstance(raw, dict) and isinstance(raw.get("prompts"), list):
        raw = raw["prompts"]

    if isinstance(raw, dict):
        return [{"key": key, "text": text} for key, text in raw.items() if isinstance(text, str)]

    if isinstance(raw, list):
        prompts: List[Dict[str, str]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key", "")).strip()
            text = str(item.get("text", "")).strip()
            if key and text:
                prompts.append({"key": key, "text": text})
        return prompts

    return []


def _get_prompt_list() -> List[Dict[str, str]]:
    file_prompts = _load_prompts_from_file()
    if file_prompts:
        return file_prompts

    try:
        legacy_prompts = getattr(config, "PROMPTS", {}) or {}
    except Exception as exc:
        logger.error("Failed to load prompts: %s", exc)
        legacy_prompts = {}

    return [{"key": key, "text": value} for key, value in legacy_prompts.items()]


def _load_prompts() -> Dict[str, str]:
    return {item["key"]: item["text"] for item in _get_prompt_list()}


def list_enhance_prompts(include_text: bool = False) -> Dict[str, Any]:
    prompt_list = _get_prompt_list()
    prompts_payload = []
    for item in prompt_list:
        key = item["key"]
        payload = {"key": key, "label": key.replace("_", " ").title()}
        if include_text:
            payload["text"] = item["text"]
        prompts_payload.append(payload)

    return {
        "model": getattr(config, "MODEL_IMAGE", ""),
        "prompts": prompts_payload,
    }


def save_enhance_prompts(prompts: List[Dict[str, str]]) -> Dict[str, Any]:
    cleaned: List[Dict[str, str]] = []
    seen = set()
    for item in prompts:
        key = str(item.get("key", "")).strip()
        text = str(item.get("text", "")).strip()
        if not key or not text:
            continue
        if key in seen:
            raise ValueError(f"Duplicate prompt key: {key}")
        cleaned.append({"key": key, "text": text})
        seen.add(key)

    if not cleaned:
        raise ValueError("At least one prompt is required")

    path = _prompts_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"prompts": cleaned}, indent=2), encoding="utf-8")

    return list_enhance_prompts(include_text=True)


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


def traditional_upscale(
    image_path: Path,
    output_dir: Path,
    scale: int = 2,
    target_size_mb: float = 8.0,
) -> Tuple[Path | None, str | None]:
    """
    Upscale image using traditional Lanczos interpolation.
    Returns (output_path, error_message).
    """
    try:
        with Image.open(image_path) as img:
            original_size = image_path.stat().st_size / (1024 * 1024)
            logger.info(f"Traditional upscaling {image_path.name} (current: {original_size:.2f} MB)")
            
            # If already at or above target, return original
            if original_size >= target_size_mb:
                logger.info(f"Image already {original_size:.2f} MB, skipping traditional upscale")
                return None, None
            
            # Calculate new dimensions
            new_width = img.width * scale
            new_height = img.height * scale
            
            logger.info(f"Upscaling from {img.width}x{img.height} to {new_width}x{new_height} using Lanczos")
            
            # Upscale using Lanczos resampling (high quality)
            upscaled = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Save as PNG to preserve quality
            output_path = output_dir / f"{image_path.stem}_lanczos_{scale}x.png"
            upscaled.save(output_path, "PNG", optimize=False)
            
            output_size = output_path.stat().st_size / (1024 * 1024)
            logger.info(f"✅ Traditional upscale complete: {output_path.name} ({output_size:.2f} MB)")
            
            return output_path, None
            
    except Exception as e:
        error_msg = f"Traditional upscale failed: {str(e)}"
        logger.error(error_msg)
        return None, error_msg


# === Gemini Models ===

def _gemini_models_file_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "gemini_models.json"


def _load_gemini_models() -> List[Dict[str, Any]]:
    """Load Gemini models configuration from JSON file."""
    path = _gemini_models_file_path()
    if not path.exists():
        # Return defaults if no file
        return [
            {
                "id": "gemini-2.5-flash-image",
                "name": "Gemini 2.5 Flash Image",
                "description": "Latest fast image generation model",
                "active": True,
            },
            {
                "id": "gemini-3-pro-image",
                "name": "Gemini 3 Pro Image",
                "description": "Advanced professional image generation",
                "active": True,
            },
        ]

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("models", [])
    except Exception as exc:
        logger.error("Failed to read Gemini models JSON: %s", exc)
        return []


def list_gemini_models() -> List[Dict[str, Any]]:
    """Get list of available Gemini models."""
    models = _load_gemini_models()
    return [{"id": m.get("id"), "name": m.get("name"), "description": m.get("description")}
            for m in models if m.get("active")]


def save_gemini_models(models: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """Save Gemini models configuration to JSON file."""
    try:
        path = _gemini_models_file_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "models": models,
            "default_model": models[0].get("id") if models else "gemini-2.5-flash-image"
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.info(f"Saved {len(models)} Gemini models to {path.name}")
        return True, "Models saved successfully"
    except Exception as e:
        error_msg = f"Failed to save models: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


# === Enhance (AI) ===

def enhance_images_for_sku(
    sku: str,
    filenames: List[str],
    prompt_key: str,
    upscale: bool = True,
    target_size_mb: float = 8.0,
    gemini_model: str | None = None,
) -> Dict[str, Any]:
    from agents.image_generator import generate_enhanced_image  # type: ignore
    from app.services.replicate_upscaler import upscale_to_target_size

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
            source_path, prompt_key, prompt_text, output_dir=sku_dir, gemini_model=gemini_model
        )
        if error:
            error_msg = f"{filename}: {error}"
            logger.error(f"❌ Enhancement error: {error_msg}")
            errors.append(error_msg)
            continue

        # Upscale the generated image if requested
        if upscale and output_path:
            # Traditional upscaling via Lanczos interpolation (4x only)
            logger.info(f"Traditional upscaling 4x enhanced image: {output_path.name}")
            lanczos_4x_path, lanczos_4x_error = traditional_upscale(
                output_path,
                sku_dir,
                scale=4,
                target_size_mb=target_size_mb,
            )
            
            if lanczos_4x_error:
                logger.warning(f"Traditional 4x upscaling failed for {output_path.name}: {lanczos_4x_error}")
                errors.append(f"{filename}: traditional 4x upscaling failed - {lanczos_4x_error}")
            elif lanczos_4x_path and lanczos_4x_path != output_path:
                logger.info(f"Successfully traditionally upscaled 4x to {lanczos_4x_path.name}")
                
                # Delete original Gemini output after successful upscaling
                try:
                    output_path.unlink()
                    logger.info(f"Removed original Gemini image: {output_path.name}")
                except Exception as e:
                    logger.warning(f"Failed to remove original image: {e}")
                
                # Add traditional 4x upscaled version to metadata
                if lanczos_4x_path.name not in existing:
                    enhanced.append({
                        "filename": lanczos_4x_path.name,
                        "source": filename,
                        "prompt": prompt_key,
                        "generated": True,
                        "upscaled": True,
                        "upscale_method": "lanczos-4x",
                    })
                    existing.add(lanczos_4x_path.name)
                    generated.append(lanczos_4x_path.name)
        else:
            # If not upscaling, keep the original
            if output_path and output_path.name not in existing:
                enhanced.append({
                    "filename": output_path.name,
                    "source": filename,
                    "prompt": prompt_key,
                    "generated": True,
                    "upscaled": False,
                })
                existing.add(output_path.name)
                generated.append(output_path.name)

    images_section["enhanced"] = enhanced
    _update_images_summary(images_section)
    product_json["Images"] = images_section
    write_sku_json(sku, product_json)

    return {
        "success": len(generated) > 0,
        "message": "Enhanced and upscaled images generated" if upscale and generated else "Enhanced images generated" if generated else "No images generated",
        "sku": sku,
        "prompt_key": prompt_key,
        "processed_count": len(generated),
        "generated": generated,
        "errors": errors,
    }


def enhance_images_batch(
    images: List[Dict[str, str]],
    prompt_key: str,
    upscale: bool = True,
    target_size_mb: float = 8.0,
    gemini_model: str | None = None,
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
        result = enhance_images_for_sku(
            sku, 
            filenames, 
            prompt_key,
            upscale=upscale,
            target_size_mb=target_size_mb,
            gemini_model=gemini_model,
        )
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
        "message": "Batch enhancement and upscaling completed" if upscale else "Batch enhancement completed",
        "processed_count": processed_count,
        "prompt_key": prompt_key,
        "upscale": upscale,
        "target_size_mb": target_size_mb,
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
