"""
Service layer for product detail operations.
Reads JSON storage and transforms to stable API models.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

from app.models.product_detail import (
    ProductDetailCategory,
    ProductDetailField,
    ProductDetailResponse,
)
from app.repositories.sku_json_repo import read_sku_json

# Load config for products directory
LEGACY = Path(__file__).resolve().parents[2] / "legacy"
sys.path.insert(0, str(LEGACY))
import config  # type: ignore


# Fields that should be highlighted in UI as important
HIGHLIGHTED_FIELDS = {
    'gender', 'brand', 'color', 'size', 
    'more details', 'keywords', 'materials'
}


def get_product_detail(sku: str) -> ProductDetailResponse:
    """
    Get complete product details for a SKU.
    
    Transforms JSON storage format into stable API response model.
    Categories like 'Images' are excluded from the response.
    """
    product_json = read_sku_json(sku)
    
    if not product_json:
        return ProductDetailResponse(
            sku=sku,
            exists=False,
            categories=[],
            total_categories=0,
            total_fields=0,
            filled_fields=0,
            completion_percentage=0.0
        )
    
    categories: List[ProductDetailCategory] = []
    total_fields = 0
    filled_fields = 0
    
    # Iterate through JSON categories
    for category_name, fields_dict in product_json.items():
        # Skip special categories that aren't product details
        if category_name == "Images" or not isinstance(fields_dict, dict):
            continue
        
        # Build fields list for this category
        category_fields: List[ProductDetailField] = []
        for field_name, field_value in fields_dict.items():
            total_fields += 1
            
            # Convert value to string
            value_str = str(field_value) if field_value is not None else ""
            
            # Track non-empty fields
            if value_str and value_str.strip():
                filled_fields += 1
            
            # Check if field should be highlighted
            is_highlighted = field_name.strip().lower() in HIGHLIGHTED_FIELDS
            
            category_fields.append(
                ProductDetailField(
                    name=field_name,
                    value=value_str,
                    is_highlighted=is_highlighted
                )
            )
        
        # Add category if it has fields
        if category_fields:
            categories.append(
                ProductDetailCategory(
                    name=category_name,
                    fields=category_fields
                )
            )
    
    # Calculate completion percentage
    completion = (filled_fields / total_fields * 100) if total_fields > 0 else 0.0
    
    return ProductDetailResponse(
        sku=sku,
        exists=True,
        categories=categories,
        total_categories=len(categories),
        total_fields=total_fields,
        filled_fields=filled_fields,
        completion_percentage=round(completion, 1)
    )


def update_product_detail(sku: str, updates: Dict[str, Dict[str, str]]) -> tuple[bool, str, int]:
    """
    Update product detail fields.
    
    Args:
        sku: Product SKU
        updates: Dict in format {'Category Name': {'Field Name': 'New Value'}}
    
    Returns:
        Tuple of (success, message, updated_count)
    """
    # Read current product data
    product_json = read_sku_json(sku)
    
    if not product_json:
        # Create new product structure if it doesn't exist
        product_json = {}
    
    updated_count = 0
    
    # Apply updates
    for category_name, fields in updates.items():
        # Skip Images category
        if category_name == "Images":
            continue
        
        # Ensure category exists
        if category_name not in product_json:
            product_json[category_name] = {}
        
        # Ensure category is a dict
        if not isinstance(product_json[category_name], dict):
            product_json[category_name] = {}
        
        # Update fields
        for field_name, new_value in fields.items():
            product_json[category_name][field_name] = new_value
            updated_count += 1
    
    # Save back to JSON file
    products_dir = Path(getattr(config, "PRODUCTS_FOLDER_PATH"))
    sku_file = products_dir / f"{sku}.json"
    
    try:
        sku_file.parent.mkdir(parents=True, exist_ok=True)
        with sku_file.open("w", encoding="utf-8") as f:
            json.dump({sku: product_json}, f, ensure_ascii=False, indent=2)
        
        return True, f"Successfully updated {updated_count} field(s)", updated_count
    
    except Exception as e:
        return False, f"Failed to save: {str(e)}", 0
