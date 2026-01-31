"""Migration script to add missing category sections to all existing SKU JSONs.

This script:
1. Reads all existing JSON files in products folder
2. For each SKU, loads data from the Excel inventory
3. Adds missing category sections from CATEGORY_COLUMNS
4. Preserves existing data (only fills empty sections)
5. Writes back to the JSON files
"""

import json
import math
import numpy as np
from datetime import datetime, date
from pathlib import Path
import sys
from typing import Dict, Any

import pandas as pd

LEGACY = Path(__file__).resolve().parents[2] / "legacy"
sys.path.insert(0, str(LEGACY))
import config  # type: ignore


# Category columns mapping (must match json_generation.py)
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
    """Sanitize a value for JSON serialization."""
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except Exception:
        pass

    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if hasattr(v, "to_pydatetime"):
        return v.to_pydatetime().isoformat()

    if isinstance(v, np.generic):
        v = v.item()

    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return None
        return round(v, 2)

    return v


def migrate_all_jsons():
    """Add missing category sections to all existing SKU JSONs."""
    
    # Load inventory once
    print("[MIGRATION] Loading inventory database...")
    try:
        inventory_df = pd.read_excel(
            config.INVENTORY_FILE_PATH,
            sheet_name=config.INVENTORY_SHEET_NAME
        )
    except Exception as e:
        print(f"[MIGRATION ERROR] Failed to load inventory: {e}")
        return
    
    products_path = Path(config.PRODUCTS_FOLDER_PATH).resolve()
    if not products_path.exists():
        print(f"[MIGRATION ERROR] Products folder not found: {products_path}")
        return
    
    # Find all JSON files
    json_files = list(products_path.glob("*.json"))
    print(f"[MIGRATION] Found {len(json_files)} JSON files to process")
    
    updated_count = 0
    skipped_count = 0
    error_count = 0
    
    for json_file in sorted(json_files):
        try:
            sku = json_file.stem  # filename without .json
            
            # Read existing JSON
            with json_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            
            if not isinstance(data, dict) or sku not in data:
                print(f"[SKIP] {sku}: Invalid JSON structure")
                skipped_count += 1
                continue
            
            sku_data = data[sku]
            
            # Find SKU in inventory
            sku_series = inventory_df[config.SKU_COLUMN].fillna("").astype(str)
            rows = inventory_df[sku_series == sku]
            
            if rows.empty:
                print(f"[SKIP] {sku}: Not found in inventory")
                skipped_count += 1
                continue
            
            # Get row data
            row = rows.iloc[0]
            row_data = {k: _to_json_safe(v) for k, v in row.to_dict().items()}
            
            # Track if we made changes
            made_changes = False
            
            # Add missing categories
            for category, columns in CATEGORY_COLUMNS.items():
                if category not in sku_data:
                    # Add complete category section
                    category_data = {}
                    for col in columns:
                        if col in row_data:
                            category_data[col] = row_data[col]
                    
                    if category_data:  # Only add if there's data
                        sku_data[category] = category_data
                        made_changes = True
                        print(f"[ADD] {sku}: Added '{category}' section")
                else:
                    # Category exists, check for missing fields
                    category_data = sku_data[category]
                    for col in columns:
                        if col not in category_data and col in row_data:
                            category_data[col] = row_data[col]
                            made_changes = True
                            print(f"[ADD FIELD] {sku}: Added '{category}.{col}'")
            
            # Reorder categories for consistency
            ordered = {}
            for cat in CATEGORY_COLUMNS.keys():
                if cat in sku_data:
                    ordered[cat] = sku_data[cat]
            for cat in sku_data.keys():
                if cat not in ordered:
                    ordered[cat] = sku_data[cat]
            
            data[sku] = ordered
            
            # Write back if changes were made
            if made_changes:
                with json_file.open("w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                updated_count += 1
                print(f"[UPDATED] {sku}")
            else:
                print(f"[OK] {sku}: Already complete")
        
        except Exception as e:
            print(f"[ERROR] {json_file.name}: {e}")
            error_count += 1
    
    print(f"\n[MIGRATION COMPLETE]")
    print(f"  Updated: {updated_count}")
    print(f"  Skipped: {skipped_count}")
    print(f"  Errors:  {error_count}")


if __name__ == "__main__":
    migrate_all_jsons()
