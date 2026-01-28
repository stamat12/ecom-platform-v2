"""Service layer for main image operations."""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any
import sys

# Add legacy to path
LEGACY = Path(__file__).resolve().parents[2] / "legacy"
sys.path.insert(0, str(LEGACY))
import config


def _load_product_json(sku: str) -> Dict[str, Any]:
    """Load product JSON file for a SKU."""
    product_path = Path(config.PRODUCTS_FOLDER_PATH) / f"{sku}.json"
    if not product_path.exists():
        return {}
    
    try:
        with product_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get(sku, {}) if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_product_json(sku: str, product_detail: Dict[str, Any]) -> None:
    """Save product JSON file for a SKU."""
    product_path = Path(config.PRODUCTS_FOLDER_PATH) / f"{sku}.json"
    product_path.parent.mkdir(parents=True, exist_ok=True)
    
    with product_path.open("w", encoding="utf-8") as f:
        json.dump({sku: product_detail}, f, ensure_ascii=False, indent=2)


def mark_main_images(sku: str, filenames: List[str]) -> Dict[str, Any]:
    """
    Mark images as main images for a SKU.
    
    Args:
        sku: SKU identifier
        filenames: List of image filenames to mark as main
    
    Returns:
        Dict with success, message, sku, processed_count
    """
    try:
        product_detail = _load_product_json(sku) or {}
        images_section = product_detail.get("Images", {})
        if not isinstance(images_section, dict):
            images_section = {}
        
        # Get existing main_images or initialize
        main_images = list(images_section.get("main_images", []) or [])
        
        # Get existing filenames to avoid duplicates
        existing_filenames = {
            entry.get("filename") for entry in main_images 
            if isinstance(entry, dict) and entry.get("filename")
        }
        
        # Add new images
        processed = 0
        for filename in filenames:
            if filename not in existing_filenames:
                main_images.append({"filename": filename})
                existing_filenames.add(filename)
                processed += 1
        
        # Update Images section
        images_section["main_images"] = main_images
        
        # Update summary if exists
        if "schema_version" in images_section and "summary" in images_section:
            images_section["summary"]["has_main_images"] = bool(main_images)
            images_section["summary"]["count_main_images"] = len(main_images)
        
        product_detail["Images"] = images_section
        
        # Save JSON
        _save_product_json(sku, product_detail)
        
        return {
            "success": True,
            "message": f"Marked {processed} image(s) as main",
            "sku": sku,
            "processed_count": processed
        }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"Error marking main images: {str(e)}",
            "sku": sku,
            "processed_count": 0
        }


def unmark_main_images(sku: str, filenames: List[str]) -> Dict[str, Any]:
    """
    Unmark images as main images for a SKU.
    
    Args:
        sku: SKU identifier
        filenames: List of image filenames to unmark
    
    Returns:
        Dict with success, message, sku, processed_count
    """
    try:
        product_detail = _load_product_json(sku) or {}
        images_section = product_detail.get("Images", {})
        if not isinstance(images_section, dict):
            images_section = {}
        
        # Get existing main_images
        main_images = list(images_section.get("main_images", []) or [])
        
        # Remove specified filenames
        filenames_set = set(filenames)
        before_count = len(main_images)
        main_images = [
            entry for entry in main_images
            if isinstance(entry, dict) and entry.get("filename") not in filenames_set
        ]
        processed = before_count - len(main_images)
        
        # Update Images section
        images_section["main_images"] = main_images
        
        # Update summary if exists
        if "schema_version" in images_section and "summary" in images_section:
            images_section["summary"]["has_main_images"] = bool(main_images)
            images_section["summary"]["count_main_images"] = len(main_images)
        
        product_detail["Images"] = images_section
        
        # Save JSON
        _save_product_json(sku, product_detail)
        
        return {
            "success": True,
            "message": f"Unmarked {processed} image(s) as main",
            "sku": sku,
            "processed_count": processed
        }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"Error unmarking main images: {str(e)}",
            "sku": sku,
            "processed_count": 0
        }


def get_main_images(sku: str) -> List[str]:
    """
    Get list of main image filenames for a SKU.
    
    Args:
        sku: SKU identifier
    
    Returns:
        List of main image filenames
    """
    try:
        product_detail = _load_product_json(sku)
        images_section = product_detail.get("Images", {})
        if not isinstance(images_section, dict):
            return []
        
        main_images = images_section.get("main_images", []) or []
        return [
            entry.get("filename") 
            for entry in main_images 
            if isinstance(entry, dict) and entry.get("filename")
        ]
    except Exception:
        return []


def is_main_image(sku: str, filename: str) -> bool:
    """
    Check if an image is marked as main.
    
    Args:
        sku: SKU identifier
        filename: Image filename
    
    Returns:
        True if image is main, False otherwise
    """
    main_images = get_main_images(sku)
    return filename in main_images
