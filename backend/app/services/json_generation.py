"""Service to check and generate JSON files for SKUs from inventory database.

This service mirrors the ecommerceAI inventory_data_collector agent, but keeps
the agent logic encapsulated in a service layer with stable Pydantic schemas
for the API layer.
"""
import json
import math
import numpy as np
from datetime import datetime, date
from pathlib import Path
import sys

import pandas as pd

LEGACY = Path(__file__).resolve().parents[2] / "legacy"
sys.path.insert(0, str(LEGACY))
import config  # type: ignore

# Load category mapping once at import time
_CATEGORY_MAPPING_CACHE = None

def _load_category_mapping():
    """Load category mapping from JSON file."""
    global _CATEGORY_MAPPING_CACHE
    if _CATEGORY_MAPPING_CACHE is not None:
        return _CATEGORY_MAPPING_CACHE
    
    try:
        mapping_path = Path(__file__).resolve().parents[2] / "schemas" / "category_mapping.json"
        if mapping_path.exists():
            with open(mapping_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                _CATEGORY_MAPPING_CACHE = data.get('categoryMappings', [])
                return _CATEGORY_MAPPING_CACHE
    except Exception as e:
        print(f"[CATEGORY MAPPING] Error loading: {e}")
    
    return []

def get_category_id_for_path(category_path: str) -> str:
    """Look up CategoryID from category path using category_mapping.json.
    
    Args:
        category_path: The full path like "/Kleidung & Accessoires/Herren/Herrenschuhe/Sneaker"
    
    Returns:
        The categoryId as string, or empty string if not found
    """
    if not category_path:
        return ""
    
    category_path = category_path.strip()
    mappings = _load_category_mapping()
    
    # Search for exact match
    for mapping in mappings:
        if mapping.get('fullPath') == category_path:
            return str(mapping.get('categoryId', ''))
    
    return ""



# Column categories mirroring inventory_data_collector.py
CATEGORY_COLUMNS = {
    "Invoice Data": [
        config.BUYING_ENTITY_COLUMN,
        config.SUPPLIER_COLUMN,
        config.INVOICE_COLUMN,
        config.INVOICE_DATE_COLUMN,
    ],
    "Supplier Data": [
        config.SUPPLIER_NUMBER_COLUMN,
        config.ISIN_COLUMN,
        config.TITLE_COLUMN,
    ],
    "Price Data": [
        config.PRICE_NET_COLUMN,
        config.SHIPPING_NET_COLUMN,
        config.TOTAL_COST_NET_COLUMN,
    ],
    "Ebay Category": [
        config.CATEGORY_COLUMN,
    ],
    "EAN": [
        config.EAN_COLUMN,
    ],
    "Product Condition": [
        config.CONDITION_COLUMN,
    ],
    "Intern Product Info": [
        config.GENDER_COLUMN,
        config.BRAND_COLUMN,
        config.COLOR_COLUMN,
        config.SIZE_COLUMN,
    ],
    "Intern Generated Info": [
        config.MORE_DETAILS_COLUMN,
        config.KEYWORDS_COLUMN,
        config.MATERIALS_COLUMN,
    ],
    "OP": [
        config.OP_COLUMN,
    ],
    "Status": [
        config.STATUS_COLUMN,
    ],
    "Warehouse": [
        config.LAGER_COLUMN,
    ],
}


def _to_json_safe(v):
    """Sanitize a value for JSON serialization.
    
    Handles pandas NaN, numpy scalars, datetime objects, and floats.
    """
    # Missing values
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except Exception:
        pass

    # Datetime/date (pandas Timestamp also works)
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if hasattr(v, "to_pydatetime"):  # pandas Timestamp
        return v.to_pydatetime().isoformat()

    # Numpy scalars -> python scalars
    if isinstance(v, np.generic):
        v = v.item()

    # Floats: protect NaN/Inf
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return None
        return round(v, 2)

    # ints/bools/strings are fine
    return v


def check_json_exists(sku: str) -> bool:
    """Check if JSON file exists for a SKU."""
    try:
        products_path = Path(config.PRODUCTS_FOLDER_PATH).resolve()
        json_file = products_path / f"{sku}.json"
        exists = json_file.exists()
        print(f"[JSON CHECK] SKU: {sku}, Path: {json_file}, Exists: {exists}")
        return exists
    except Exception as e:
        print(f"[JSON CHECK ERROR] SKU: {sku}, Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_json_from_inventory(sku: str) -> dict:
    """Create JSON for a SKU from inventory database.
    
    Mirrors ecommerceAI's inventory_data_collector.export_sku_records().
    Organizes inventory columns by category and preserves existing
    non-inventory sections (like Images).
    
    Args:
        sku: The SKU identifier (must match SKU_COLUMN in inventory)
    
    Returns:
        Dictionary with keys: success (bool), message (str), sku (str)
    """
    try:
        # Load inventory
        inventory_df = pd.read_excel(
            config.INVENTORY_FILE_PATH,
            sheet_name=config.INVENTORY_SHEET_NAME
        )
        
        # Find row for this SKU
        sku_series = inventory_df[config.SKU_COLUMN].fillna("").astype(str)
        rows = inventory_df[sku_series == sku]
        
        if rows.empty:
            return {
                "success": False,
                "message": f"SKU {sku} not found in inventory database",
                "sku": sku,
            }
        
        # Sanitize all values in the row
        row = rows.iloc[0]
        row_data = {k: _to_json_safe(v) for k, v in row.to_dict().items()}

        # Build payload organized by categories (including all categories, even if empty)
        payload = {sku: {}}
        for category, columns in CATEGORY_COLUMNS.items():
            category_data = {}
            for col in columns:
                if col in row_data:
                    category_data[col] = row_data[col]
            # Always add the category section, even if empty
            payload[sku][category] = category_data
        
        # For Ebay Category, look up and add the CategoryID if Category is present
        if "Ebay Category" in payload[sku]:
            category_path = payload[sku]["Ebay Category"].get("Category", "")
            if category_path:
                category_id = get_category_id_for_path(category_path)
                if category_id:
                    payload[sku]["Ebay Category"]["eBay Category ID"] = category_id
        
        # Ensure OP is float with 2 decimals
        try:
            op_key = config.OP_COLUMN
            if "OP" in payload[sku] and op_key in payload[sku]["OP"]:
                val = payload[sku]["OP"][op_key]
                if val is not None and val != "":
                    payload[sku]["OP"][op_key] = round(float(val), 2)
        except Exception:
            pass
        
        # Write to products folder
        products_path = Path(config.PRODUCTS_FOLDER_PATH)
        products_path.mkdir(exist_ok=True)
        output_file = products_path / f"{sku}.json"
        
        # Merge with existing if exists (preserves Images and other sections)
        to_write = payload
        if output_file.exists():
            try:
                with output_file.open("r", encoding="utf-8") as f:
                    existing = json.load(f)
                existing_data = existing.get(sku, {}) if isinstance(existing, dict) else {}
                merged = existing_data.copy()
                
                # Update inventory sections
                for cat, cat_data in payload.get(sku, {}).items():
                    merged[cat] = cat_data
                
                # Reorder categories: follow CATEGORY_COLUMNS order, then others (e.g., Images)
                ordered = {}
                for cat in CATEGORY_COLUMNS.keys():
                    if cat in merged:
                        ordered[cat] = merged[cat]
                for cat in merged.keys():
                    if cat not in ordered:
                        ordered[cat] = merged[cat]
                
                to_write = {sku: ordered}
            except Exception:
                to_write = payload
        
        # Write file
        with output_file.open("w", encoding="utf-8") as f:
            json.dump(to_write, f, ensure_ascii=False, indent=2)
        
        return {
            "success": True,
            "message": f"JSON created/updated for SKU {sku} from inventory database",
            "sku": sku,
        }
    
    except FileNotFoundError:
        return {
            "success": False,
            "message": f"Inventory file not found at {config.INVENTORY_FILE_PATH}",
            "sku": sku,
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error creating JSON from inventory: {str(e)}",
            "sku": sku,
        }


def generate_json_for_sku(sku: str) -> dict:
    """Generate/create JSON for a SKU.
    
    If JSON already exists, returns success (no-op).
    If JSON doesn't exist, creates it from inventory database.
    
    Args:
        sku: The SKU identifier
    
    Returns:
        Dictionary with success status and message
    """
    if check_json_exists(sku):
        return {
            "success": True,
            "message": f"JSON already exists for SKU {sku}",
            "sku": sku,
        }
    
    return create_json_from_inventory(sku)

