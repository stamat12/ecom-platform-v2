"""Upscale images using Real-ESRGAN via Replicate API."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional, Tuple
from urllib.request import urlopen

import replicate

# Resolve project root and import config
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import config  # noqa: E402


def upscale_image(
    image_path: Path,
    output_dir: Optional[Path] = None,
    scale: int = 4,
) -> Tuple[Optional[Path], Optional[str]]:
    """Upscale image using Real-ESRGAN via Replicate.
    
    Args:
        image_path: Path to the source image
        output_dir: Directory to save the upscaled image (defaults to source dir)
        scale: Upscaling factor (2, 3, or 4; default 4)
    
    Returns:
        (output_path, error_message) - returns path if success, (None, error_msg) if failed
    """
    # Ensure Path objects
    image_path = Path(image_path) if isinstance(image_path, str) else image_path
    output_dir = Path(output_dir) if isinstance(output_dir, str) else output_dir if output_dir else None
    
    if not image_path.exists():
        return None, f"Source image not found: {image_path}"

    output_dir = output_dir or image_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine output filename
    stem = image_path.stem
    upscaled_filename = f"{stem}_upscaled_x{scale}.jpg"
    output_path = output_dir / upscaled_filename

    # Check for API token
    api_token = os.getenv("REPLICATE_API_TOKEN")
    if not api_token:
        return None, "REPLICATE_API_TOKEN environment variable not set"

    try:
        # Call Real-ESRGAN model via Replicate
        # We use the OFFICIAL nightmareai/real-esrgan model which runs on the T4 GPU
        output = replicate.run(
            "nightmareai/real-esrgan:42fed1c4974146d4d2414e2be2c5277c7fcf05fcc3a73abf41610695738c1d7b",
            input={
                "image": open(image_path, "rb"),
                "scale": scale,
                "face_enhance": False
            },
            api_token=api_token,
        )

        if not output:
            return None, "Real-ESRGAN API returned no output"

        # output is typically a URL string
        output_url = str(output).strip()

        # Download the upscaled image from the URL
        try:
            with urlopen(output_url) as response:
                image_bytes = response.read()
        except Exception as ex:
            return None, f"Failed to download upscaled image from {output_url}: {str(ex)}"

        # Save the upscaled image
        try:
            with output_path.open("wb") as f:
                f.write(image_bytes)
        except Exception as ex:
            return None, f"Failed to save upscaled image: {str(ex)}"

        return output_path, None

    except Exception as ex:
        return None, f"Real-ESRGAN upscaling failed: {str(ex)}"


def upscale_and_update_json(
    sku: str,
    image_filename: str,
    original_image_path: Path,
    output_dir: Optional[Path] = None,
    scale: int = 4,
) -> Tuple[Optional[Path], Optional[str]]:
    """Upscale image and update SKU JSON with upscaled version.
    
    Args:
        sku: SKU identifier
        image_filename: Filename of the image to upscale
        original_image_path: Full path to the image file
        output_dir: Output directory for upscaled image
        scale: Upscaling factor
    
    Returns:
        (output_path, error_message)
    """
    # Upscale the image
    upscaled_path, upscale_error = upscale_image(
        original_image_path, output_dir, scale
    )

    if upscale_error:
        return None, upscale_error

    # Update JSON to reference upscaled version
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

        # Add upscaled image to enhanced category
        enhanced = images_section.get("enhanced", []) or []
        # Check if already exists to avoid duplicates
        if not any(r.get("filename") == upscaled_path.name for r in enhanced):
            enhanced.append({
                "filename": upscaled_path.name,
                "source": image_filename,
                "upscaled": True,
                "scale": scale,
            })

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

        return upscaled_path, None

    except Exception as ex:
        return None, f"Failed to update JSON: {str(ex)}"