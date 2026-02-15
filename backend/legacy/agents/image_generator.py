"""Generate enhanced images using Gemini image model."""
from __future__ import annotations

import base64
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Optional, Tuple

import google.generativeai as genai

# Resolve project root and import config
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import config  # noqa: E402

logger = logging.getLogger(__name__)

# Set up file logging
def _setup_file_logging():
    """Configure file logging for image generation."""
    log_dir = Path(__file__).resolve().parents[2] / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "image_generator.log"
    
    handler = logging.FileHandler(log_file, encoding="utf-8")
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

_setup_file_logging()


def encode_image_to_base64(image_path: Path) -> str:
    """Encode image file to base64 string."""
    with image_path.open("rb") as img_file:
        return base64.standard_b64encode(img_file.read()).decode("utf-8")


def get_mime_type(image_path: Path) -> str:
    """Get proper MIME type for image file."""
    suffix = image_path.suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
    }
    return mime_map.get(suffix, "image/jpeg")


def _slugify_model_id(model_id: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", model_id or "").strip("-").lower()
    return cleaned or "gemini"


def generate_enhanced_image(
    image_path: Path,
    prompt_name: str,
    prompt_text: str,
    output_dir: Optional[Path] = None,
    gemini_model: Optional[str] = None,
) -> Tuple[Optional[Path], Optional[str]]:
    """Generate enhanced image using Gemini image model.
    
    Args:
        image_path: Path to the source image
        prompt_name: Name of the prompt (e.g., 'studio_restoration')
        prompt_text: The actual prompt text from PROMPTS dict
        output_dir: Directory to save the generated image (defaults to source dir)
        gemini_model: Gemini model to use (defaults to config.MODEL_IMAGE)
    
    Returns:
        (output_path, error_message) - returns path if success, (None, error_msg) if failed
    """
    if not image_path.exists():
        return None, f"Source image not found: {image_path}"

    output_dir = output_dir or image_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine output filename
    stem = image_path.stem
    suffix = image_path.suffix
    model_id = gemini_model or config.MODEL_IMAGE
    model_slug = _slugify_model_id(model_id)

    # Find next available number to avoid overwrites
    counter = 1
    while True:
        output_filename = f"{prompt_name}_{model_slug}_real_{stem}_{counter}{suffix}"
        output_path = output_dir / output_filename
        if not output_path.exists():
            break
        counter += 1

    # Initialize Gemini client
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None, "GOOGLE_API_KEY (or GEMINI_API_KEY) environment variable not set"
    genai.configure(api_key=api_key)
    
    # Use specified model or default to config
    logger.info(f"📸 Using Gemini model: {model_id}")
    model = genai.GenerativeModel(model_id)

    # Prepare payload
    image_data = encode_image_to_base64(image_path)

    try:
        logger.info(f"🚀 Sending request to {model_id}...")
        response = model.generate_content(
            [
                prompt_text,
                {
                    "mime_type": get_mime_type(image_path),
                    "data": image_data,
                },
            ],
            # response_mime_type is not allowed for this model; keep minimal config
            generation_config={
                "temperature": 0.2,
            },
        )
        logger.info(f"✅ Response received from {model_id}")
        usage = getattr(response, "usage_metadata", None)
        if usage:
            if isinstance(usage, dict):
                prompt_tokens = usage.get("prompt_token_count")
                candidates_tokens = usage.get("candidates_token_count")
                total_tokens = usage.get("total_token_count")
            else:
                prompt_tokens = getattr(usage, "prompt_token_count", None)
                candidates_tokens = getattr(usage, "candidates_token_count", None)
                total_tokens = getattr(usage, "total_token_count", None)
            logger.info(
                "🔢 Gemini usage - prompt: %s, candidates: %s, total: %s",
                prompt_tokens,
                candidates_tokens,
                total_tokens,
            )
    except Exception as ex:
        error_details = f"{type(ex).__name__}: {str(ex)}"
        logger.error(f"❌ Gemini API Error ({model_id}): {error_details}")
        return None, error_details

    # Extract image bytes from response with debug info
    image_bytes = None
    debug_parts = []
    for cand in getattr(response, "candidates", []) or []:
        content = getattr(cand, "content", None)
        if not content:
            continue
        for part in getattr(content, "parts", []) or []:
            part_kind = "unknown"
            if getattr(part, "inline_data", None) and getattr(part.inline_data, "data", None):
                part_kind = "inline_image"
                image_bytes = part.inline_data.data
                logger.info("✅ Found inline image data in response")
            elif getattr(part, "text", None):
                part_kind = "text"
                debug_parts.append(f"text[{len(part.text)}]: {part.text[:200]}")
            else:
                debug_parts.append("other part (no text/inline_data)")

            if part_kind == "inline_image":
                break
        if image_bytes:
            break

    if not image_bytes:
        if debug_parts:
            error_msg = "Gemini returned no image; parts: " + " | ".join(debug_parts)
            logger.error(f"❌ {error_msg}")
            return None, error_msg
        logger.error("❌ Gemini API returned no image data")
        return None, "Gemini API returned no image data"

    # Save image bytes
    try:
        if isinstance(image_bytes, str):
            image_bytes = base64.b64decode(image_bytes)
        with output_path.open("wb") as f:
            f.write(image_bytes)
        logger.info(f"💾 Saved image to {output_path.name}")
    except Exception as ex:
        error_msg = f"Failed to save image: {str(ex)}"
        logger.error(f"❌ {error_msg}")
        return None, error_msg

    return output_path, None


def add_generated_image_to_json(
    sku: str,
    image_filename: str,
) -> Tuple[bool, Optional[str]]:
    """Add generated image reference to SKU's JSON file in 'enhanced' category.
    
    Args:
        sku: SKU identifier
        image_filename: Filename of the generated image
    
    Returns:
        (success, error_message)
    """
    try:
        product_path = config.PRODUCTS_FOLDER_PATH / f"{sku}.json"
        
        # Load existing JSON
        if product_path.exists():
            with product_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            product_detail = data.get(sku, {})
        else:
            product_detail = {}
        
        # Ensure Images section exists
        if "Images" not in product_detail:
            product_detail["Images"] = {
                "schema_version": "1.0",
                "summary": {
                    "has_stock": False,
                    "has_phone": False,
                    "has_enhanced": False,
                    "count_stock": 0,
                    "count_phone": 0,
                    "count_enhanced": 0,
                },
                "stock": [],
                "phone": [],
                "enhanced": [],
            }
        
        images_section = product_detail["Images"]
        
        # Add to enhanced if not already there
        enhanced = images_section.get("enhanced", []) or []
        if not any(r.get("filename") == image_filename for r in enhanced):
            enhanced.append({"filename": image_filename})
        
        # Update summary
        stock = images_section.get("stock", []) or []
        phone = images_section.get("phone", []) or []
        
        images_section["summary"] = {
            "has_stock": bool(stock),
            "has_phone": bool(phone),
            "has_enhanced": bool(enhanced),
            "count_stock": len(stock),
            "count_phone": len(phone),
            "count_enhanced": len(enhanced),
        }
        images_section["enhanced"] = enhanced
        
        # Save back to JSON
        product_detail["Images"] = images_section
        
        product_path.parent.mkdir(parents=True, exist_ok=True)
        with product_path.open("w", encoding="utf-8") as f:
            json.dump({sku: product_detail}, f, ensure_ascii=False, indent=2)
        
        return True, None
    
    except Exception as ex:
        return False, f"Failed to update JSON: {str(ex)}"


def generate_and_save(
    sku: str,
    image_path: Path,
    prompt_name: str,
    prompt_text: str,
    output_dir: Optional[Path] = None,
) -> Tuple[Optional[Path], Optional[str]]:
    """Generate image and automatically add to JSON.
    
    Args:
        sku: SKU identifier
        image_path: Path to source image
        prompt_name: Name of the prompt
        prompt_text: Full prompt text
        output_dir: Output directory (defaults to image dir)
    
    Returns:
        (output_path, error_message)
    """
    # Generate the image
    output_path, gen_error = generate_enhanced_image(
        image_path, prompt_name, prompt_text, output_dir
    )
    
    if gen_error:
        return None, gen_error
    
    # Add to JSON
    success, json_error = add_generated_image_to_json(sku, output_path.name)
    
    if not success:
        return None, json_error
    
    return output_path, None
