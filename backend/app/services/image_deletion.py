"""Service for deleting images from SKU folders and metadata"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

from app.repositories.sku_json_repo import read_sku_json, write_sku_json
from app.services.image_listing import _find_sku_dir

logger = logging.getLogger(__name__)


def delete_image(sku: str, filename: str) -> Dict[str, Any]:
    """
    Delete an image from folder and from JSON metadata
    
    Args:
        sku: SKU identifier
        filename: Image filename to delete
        
    Returns:
        Dict with success status and message
    """
    sku_dir = _find_sku_dir(sku)
    if not sku_dir:
        return {
            "success": False,
            "message": f"Images folder not found for SKU {sku}",
            "sku": sku,
            "filename": filename,
        }
    
    image_path = sku_dir / filename
    
    # Delete physical file
    deleted_file = False
    if image_path.exists():
        try:
            image_path.unlink()
            logger.info(f"Deleted image file: {image_path}")
            deleted_file = True
        except Exception as e:
            logger.error(f"Failed to delete image file {image_path}: {e}")
            return {
                "success": False,
                "message": f"Failed to delete image file: {str(e)}",
                "sku": sku,
                "filename": filename,
            }
    
    # Update JSON metadata
    product_json = read_sku_json(sku) or {}
    
    # Remove from Images section
    if "Images" in product_json and isinstance(product_json["Images"], dict):
        images_section = product_json["Images"]
        
        # Remove from enhanced list
        if "enhanced" in images_section:
            enhanced = images_section.get("enhanced", [])
            if isinstance(enhanced, list):
                images_section["enhanced"] = [
                    e for e in enhanced
                    if not (isinstance(e, dict) and e.get("filename") == filename)
                ]
        
        # Remove from main_images
        main_images = images_section.get("main_images", [])
        if isinstance(main_images, list) and filename in main_images:
            images_section["main_images"] = [f for f in main_images if f != filename]
        
        # Update summary
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
        
        product_json["Images"] = images_section
    
    # Remove from ebay_images if present
    if "Ebay_Images" in product_json and isinstance(product_json["Ebay_Images"], list):
        product_json["Ebay_Images"] = [
            f for f in product_json["Ebay_Images"] if f != filename
        ]
    
    # Save updated JSON
    try:
        write_sku_json(sku, product_json)
        logger.info(f"Updated JSON metadata for SKU {sku}, removed {filename}")
    except Exception as e:
        logger.error(f"Failed to update JSON metadata for SKU {sku}: {e}")
        return {
            "success": False,
            "message": f"Failed to update metadata: {str(e)}",
            "sku": sku,
            "filename": filename,
        }
    
    return {
        "success": True,
        "message": f"Image {filename} deleted successfully",
        "sku": sku,
        "filename": filename,
        "deleted_file": deleted_file,
    }
