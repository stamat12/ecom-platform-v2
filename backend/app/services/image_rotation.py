from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from PIL import Image

import sys
LEGACY = Path(__file__).resolve().parents[2] / "legacy"
sys.path.insert(0, str(LEGACY))
import config  # type: ignore


def _image_base_dirs() -> list[Path]:
    env_dirs = os.getenv("IMAGE_BASE_DIRS")
    if env_dirs:
        return [Path(p.strip()) for p in env_dirs.split(";") if p.strip()]
    bases = getattr(config, "IMAGE_FOLDER_PATHS", [])
    return [Path(p) for p in bases]


def _find_image_path(sku: str, filename: str) -> Optional[Path]:
    """Find the original image file path"""
    for base in _image_base_dirs():
        candidate = base / sku / filename
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def rotate_image(sku: str, filename: str, degrees: int) -> dict:
    """
    Rotate an image by the specified degrees (90, 180, or 270) and save it.
    
    Args:
        sku: The SKU identifier
        filename: The image filename
        degrees: Rotation angle (90, 180, or 270)
    
    Returns:
        Dictionary with success status and message
    """
    # Validate degrees
    if degrees not in [90, 180, 270]:
        return {
            "success": False,
            "message": f"Invalid rotation degrees: {degrees}. Must be 90, 180, or 270.",
            "sku": sku,
            "filename": filename,
            "degrees": degrees,
        }
    
    # Find the image
    image_path = _find_image_path(sku, filename)
    if not image_path:
        return {
            "success": False,
            "message": f"Image not found: {sku}/{filename}",
            "sku": sku,
            "filename": filename,
            "degrees": degrees,
        }
    
    try:
        # Open and rotate image
        with Image.open(image_path) as img:
            # Convert rotation degrees to PIL format
            # PIL rotates counter-clockwise, so we need to negate for clockwise rotation
            rotated = img.rotate(-degrees, expand=True)
            
            # Save rotated image
            rotated.save(image_path, quality=95, optimize=True)
        
        return {
            "success": True,
            "message": f"Image rotated {degrees}° successfully",
            "sku": sku,
            "filename": filename,
            "degrees": degrees,
        }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"Error rotating image: {str(e)}",
            "sku": sku,
            "filename": filename,
            "degrees": degrees,
        }


def clear_image_cache(sku: str, filename: str) -> None:
    """
    Clear cached thumbnails for an image after rotation.
    
    Args:
        sku: The SKU identifier
        filename: The image filename
    """
    from app.services.image_serving import CACHE_ROOT
    
    # Remove all cached variants
    for variant in ["thumb_256", "thumb_512"]:
        cached = CACHE_ROOT / variant / sku / filename
        if cached.exists():
            try:
                cached.unlink()
            except Exception:
                pass  # Ignore cache clearing errors
