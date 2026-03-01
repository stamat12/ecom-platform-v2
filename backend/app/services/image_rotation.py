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
            # Try to preserve EXIF data
            exif_data = img.getexif() if hasattr(img, 'getexif') else None
            
            # Convert rotation degrees to PIL format
            # PIL rotates counter-clockwise, so we need to negate for clockwise rotation
            rotated = img.rotate(-degrees, expand=True)
            
            # Save rotated image with appropriate format
            # Determine format from extension
            fmt = image_path.suffix.lower()
            if fmt in ['.jpg', '.jpeg']:
                save_kwargs = {'quality': 95, 'optimize': True}
                save_format = 'JPEG'
            elif fmt == '.png':
                save_kwargs = {'optimize': True}
                save_format = 'PNG'
            elif fmt == '.webp':
                save_kwargs = {'quality': 95}
                save_format = 'WEBP'
            else:
                save_kwargs = {}
                save_format = None
            
            # Save the rotated image
            if save_format:
                rotated.save(image_path, format=save_format, **save_kwargs)
            else:
                rotated.save(image_path, **save_kwargs)
        
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
    Clear cached thumbnails and variants for an image after rotation.
    
    Args:
        sku: The SKU identifier
        filename: The image filename
    """
    from app.services.image_serving import CACHE_ROOT
    
    # Remove all cached variants - be comprehensive
    variants = ["thumb_256", "thumb_512", "original", "display", "preview"]
    for variant in variants:
        cached = CACHE_ROOT / variant / sku / filename
        if cached.exists():
            try:
                cached.unlink()
                import logging
                logging.info(f"Cleared cache: {cached}")
            except Exception as e:
                import logging
                logging.warning(f"Failed to clear cache {cached}: {e}")
                pass  # Ignore cache clearing errors
    
    # Also try to clear parent directories if empty
    for variant in variants:
        try:
            sku_cache_dir = CACHE_ROOT / variant / sku
            if sku_cache_dir.exists() and not any(sku_cache_dir.iterdir()):
                sku_cache_dir.rmdir()
        except Exception:
            pass
