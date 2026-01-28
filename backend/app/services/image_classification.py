"""Service for image classification operations.

Wraps the image_classification agent logic in a stable service interface.
Follows architectural rules: agents behind service layer, stable Pydantic schemas.
"""
import json
from pathlib import Path
from typing import List, Optional, Tuple
import sys

LEGACY = Path(__file__).resolve().parents[2] / "legacy"
sys.path.insert(0, str(LEGACY))
import config  # type: ignore


def load_product_json(sku: str) -> dict:
    """Load product JSON for a SKU."""
    try:
        product_path = Path(config.PRODUCTS_FOLDER_PATH) / f"{sku}.json"
        if not product_path.exists():
            return {}
        with product_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get(sku, {}) if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_product_json(sku: str, product_data: dict) -> None:
    """Save product JSON for a SKU."""
    product_path = Path(config.PRODUCTS_FOLDER_PATH) / f"{sku}.json"
    product_path.parent.mkdir(parents=True, exist_ok=True)
    with product_path.open("w", encoding="utf-8") as f:
        json.dump({sku: product_data}, f, ensure_ascii=False, indent=2)


def build_images_summary(stock: List[dict], phone: List[dict], enhanced: List[dict]) -> dict:
    """Build the Images section structure with summary metadata."""
    return {
        "schema_version": "1.0",
        "summary": {
            "has_stock": bool(stock),
            "has_phone": bool(phone),
            "has_enhanced": bool(enhanced),
            "count_stock": len(stock),
            "count_phone": len(phone),
            "count_enhanced": len(enhanced),
        },
        "stock": stock,
        "phone": phone,
        "enhanced": enhanced,
    }


def get_image_classification(sku: str, filename: str) -> Optional[str]:
    """Get the current classification type for an image.
    
    Args:
        sku: The SKU identifier
        filename: The image filename
    
    Returns:
        Classification type ('phone', 'stock', 'enhanced') or None if not classified
    """
    try:
        product_data = load_product_json(sku)
        if not product_data:
            return None
        
        images_section = product_data.get("Images", {})
        if not isinstance(images_section, dict):
            return None
        
        for category in ["phone", "stock", "enhanced"]:
            images_list = images_section.get(category, []) or []
            for img_record in images_list:
                if img_record.get("filename") == filename or img_record.get("file") == filename:
                    return category
        return None
    except Exception:
        return None


def classify_images(sku: str, filenames: List[str], classification_type: str) -> dict:
    """Classify images for a SKU.
    
    Adds image filenames to the specified classification category in the JSON.
    Removes from other categories if already classified elsewhere.
    
    Args:
        sku: The SKU identifier
        filenames: List of image filenames to classify
        classification_type: Type to classify as ('phone', 'stock', 'enhanced')
    
    Returns:
        Dictionary with success, message, sku, processed_count, classification_type
    """
    if classification_type not in ("phone", "stock", "enhanced"):
        return {
            "success": False,
            "message": f"Invalid classification type: {classification_type}",
            "sku": sku,
            "processed_count": 0,
            "classification_type": classification_type,
        }
    
    if not filenames:
        return {
            "success": False,
            "message": "No filenames provided",
            "sku": sku,
            "processed_count": 0,
            "classification_type": classification_type,
        }
    
    try:
        # Load product data
        product_data = load_product_json(sku) or {}
        images_section = product_data.get("Images", {})
        if not isinstance(images_section, dict):
            images_section = {}
        
        # Get existing classifications
        stock = list(images_section.get("stock", []) or [])
        phone = list(images_section.get("phone", []) or [])
        enhanced = list(images_section.get("enhanced", []) or [])
        
        # Remove these filenames from all categories first (avoid duplicates)
        filenames_set = set(filenames)
        stock = [r for r in stock if r.get("filename") not in filenames_set and r.get("file") not in filenames_set]
        phone = [r for r in phone if r.get("filename") not in filenames_set and r.get("file") not in filenames_set]
        enhanced = [r for r in enhanced if r.get("filename") not in filenames_set and r.get("file") not in filenames_set]
        
        # Add to target category
        for filename in filenames:
            record = {"filename": filename}
            if classification_type == "phone":
                phone.append(record)
            elif classification_type == "stock":
                stock.append(record)
            elif classification_type == "enhanced":
                enhanced.append(record)
        
        # Update Images section with summary
        product_data["Images"] = build_images_summary(stock, phone, enhanced)
        
        # Save
        save_product_json(sku, product_data)
        
        return {
            "success": True,
            "message": f"Classified {len(filenames)} image(s) as {classification_type}",
            "sku": sku,
            "processed_count": len(filenames),
            "classification_type": classification_type,
        }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"Error classifying images: {str(e)}",
            "sku": sku,
            "processed_count": 0,
            "classification_type": classification_type,
        }
