"""Product data management utilities for loading and saving JSON files."""

import json
from pathlib import Path
from typing import Dict, List, Any
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import config


def load_all_products() -> List[Dict[str, Any]]:
    """Load all product JSON files and return as a list of dictionaries."""
    
    products = []
    products_dir = config.PRODUCTS_FOLDER_PATH
    
    if not products_dir.exists():
        return products
    
    for json_file in sorted(products_dir.glob("*.json")):
        try:
            with json_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Extract SKU and product data
            for sku, sku_data in data.items():
                if isinstance(sku_data, dict):
                    # Flatten nested structure
                    flat_product = {"SKU": sku, "_file": json_file.name}
                    
                    for category, fields in sku_data.items():
                        if isinstance(fields, dict):
                            for key, value in fields.items():
                                flat_product[key] = value
                        else:
                            flat_product[category] = fields
                    
                    products.append(flat_product)
        
        except Exception as e:
            print(f"Error loading {json_file.name}: {e}")
    
    return products


def save_product(sku: str, product_data: Dict[str, Any]) -> bool:
    """Save a product back to its JSON file."""
    
    try:
        products_dir = config.PRODUCTS_FOLDER_PATH
        file_path = products_dir / f"{sku}.json"
        
        with file_path.open("w", encoding="utf-8") as f:
            json.dump({sku: product_data}, f, ensure_ascii=False, indent=2)
        
        return True
    
    except Exception as e:
        print(f"Error saving {sku}: {e}")
        return False


def get_all_columns(products: List[Dict[str, Any]]) -> List[str]:
    """Get all unique column names from products."""
    
    columns = set()
    for product in products:
        columns.update(product.keys())
    
    # Remove internal columns
    columns.discard("_file")
    
    return sorted(list(columns))


def get_categorized_columns() -> Dict[str, List[str]]:
    """Get columns organized by their categories from the original JSON structure."""
    
    products_dir = config.PRODUCTS_FOLDER_PATH
    
    if not products_dir.exists():
        return {}
    
    categorized: Dict[str, set[str]] = {}

    try:
        for json_file in products_dir.glob("*.json"):
            with json_file.open("r", encoding="utf-8") as f:
                data = json.load(f)

            for _, sku_data in data.items():
                if isinstance(sku_data, dict):
                    for category, fields in sku_data.items():
                        if isinstance(fields, dict):
                            categorized.setdefault(category, set()).update(fields.keys())
                        else:
                            categorized.setdefault("Other", set()).add(category)

        return {cat: sorted(list(cols)) for cat, cols in categorized.items()}

    except Exception as e:
        print(f"Error loading categorized columns: {e}")
        return {}


def filter_products(
    products: List[Dict[str, Any]], 
    filters: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Apply filters to products list."""
    
    filtered = products
    
    for key, value in filters.items():
        if value:
            filtered = [
                p for p in filtered 
                if str(p.get(key, "")).lower().find(str(value).lower()) >= 0
            ]
    
    return filtered
