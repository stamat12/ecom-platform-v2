"""Service to sync JSON data back to Excel."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from openpyxl import load_workbook
from openpyxl.utils.dataframe import dataframe_to_rows

LEGACY = Path(__file__).resolve().parents[2] / "legacy"
import sys
sys.path.insert(0, str(LEGACY))
import config  # type: ignore

# Excel columns to sync from JSON
EXCEL_COLUMNS_TO_SYNC = [
    "Category",           # from Ebay Category section
    "EAN",                # from EAN section
    "Condition",          # from Product Condition section
    "Gender",             # from Intern Product Info section
    "Brand",              # from Intern Product Info section
    "Color",              # from Intern Product Info section
    "Size",               # from Intern Product Info section
    "More details",       # from Intern Generated Info section
    "Materials",          # from Intern Generated Info section
    "Keywords",           # from Intern Generated Info section
    "OP",                 # from OP section
    "Status",             # from Status section
    "Lager",              # from Warehouse section
    "Images JSON Phone",  # from Images section (count)
    "Images JSON Stock",  # from Images section (count)
    "Images JSON Enhanced",  # from Images section (count)
    "JSON",               # whether JSON file exists (Yes/empty)
    "Images"              # folder images count from cache
]

PRODUCTS_DIR = LEGACY / "products"


def read_sku_json(sku: str) -> Optional[Dict[str, Any]]:
    """Read JSON for a specific SKU."""
    json_file = PRODUCTS_DIR / f"{sku}.json"
    if not json_file.exists():
        return None
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # JSON structure: { "SKU": { sections... } }
            return data.get(sku, {})
    except Exception as e:
        print(f"Error reading JSON for {sku}: {e}")
        return None


def sku_json_exists(sku: str) -> str:
    """Check if JSON file exists for SKU. Returns 'Yes' or empty string."""
    json_file = PRODUCTS_DIR / f"{sku}.json"
    return "Yes" if json_file.exists() else ""


def get_folder_images_count(sku: str) -> int:
    """Get folder images count from cache for specific SKU."""
    try:
        cache_file = LEGACY / "cache" / "folder_images_cache.json"
        if not cache_file.exists():
            return 0
        
        with open(cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            counts = data.get("counts", {})
            # Get count for this specific SKU
            return counts.get(sku, 0)
    except Exception as e:
        print(f"Error reading folder images cache: {e}")
        return 0
        return 0


def get_image_counts(sku: str) -> Dict[str, int]:
    """Extract image counts from JSON."""
    json_data = read_sku_json(sku)
    if not json_data:
        return {"Images JSON Phone": 0, "Images JSON Stock": 0, "Images JSON Enhanced": 0}
    
    images = json_data.get("Images", {})
    summary = images.get("summary", {})
    
    return {
        "Images JSON Phone": summary.get("count_phone", 0),
        "Images JSON Stock": summary.get("count_stock", 0),
        "Images JSON Enhanced": summary.get("count_enhanced", 0)
    }


def flatten_json_sections(sku: str) -> Dict[str, Any]:
    """Flatten JSON sections into a single dict for Excel columns."""
    json_data = read_sku_json(sku)
    if not json_data:
        return {}
    
    flattened = {}
    
    # Ebay Category section -> Category column (the path) and we don't update Category ID in Excel
    ebay_cat = json_data.get("Ebay Category", {})
    if ebay_cat:
        flattened["Category"] = ebay_cat.get("Category")
    
    # EAN section -> EAN column
    ean_section = json_data.get("EAN", {})
    if ean_section:
        flattened["EAN"] = ean_section.get("EAN")
    
    # Product Condition section -> Condition column
    condition_section = json_data.get("Product Condition", {})
    if condition_section:
        flattened["Condition"] = condition_section.get("Condition")
    
    # Intern Product Info section -> Gender, Brand, Color, Size columns
    product_info = json_data.get("Intern Product Info", {})
    if product_info:
        flattened["Gender"] = product_info.get("Gender")
        flattened["Brand"] = product_info.get("Brand")
        flattened["Color"] = product_info.get("Color")
        flattened["Size"] = product_info.get("Size")
    
    # Intern Generated Info section -> More details, Materials, Keywords columns
    generated_info = json_data.get("Intern Generated Info", {})
    if generated_info:
        flattened["More details"] = generated_info.get("More details")
        flattened["Materials"] = generated_info.get("Materials")
        flattened["Keywords"] = generated_info.get("Keywords")
    
    # OP section -> OP column
    op_section = json_data.get("OP", {})
    if op_section:
        flattened["OP"] = op_section.get("OP")
    
    # Status section -> Status column
    status_section = json_data.get("Status", {})
    if status_section:
        flattened["Status"] = status_section.get("Status")
    
    # Warehouse section -> Lager column
    warehouse_section = json_data.get("Warehouse", {})
    if warehouse_section:
        flattened["Lager"] = warehouse_section.get("Lager")
    
    # Add image counts
    image_counts = get_image_counts(sku)
    flattened["Images JSON Phone"] = image_counts.get("Images JSON Phone", 0)
    flattened["Images JSON Stock"] = image_counts.get("Images JSON Stock", 0)
    flattened["Images JSON Enhanced"] = image_counts.get("Images JSON Enhanced", 0)
    
    # Add JSON file existence check
    flattened["JSON"] = sku_json_exists(sku)
    
    # Add folder images count from cache
    flattened["Images"] = get_folder_images_count(sku)
    
    return flattened


def detect_changes(current_values: Dict[str, Any], new_values: Dict[str, Any]) -> bool:
    """Detect if there are any changes between current and new values."""
    for key in set(list(current_values.keys()) + list(new_values.keys())):
        curr = current_values.get(key)
        new = new_values.get(key)
        
        # Normalize JSON strings for comparison
        if isinstance(curr, str) and curr and curr[0] in '{[':
            try:
                curr = json.loads(curr)
            except:
                pass
        
        if isinstance(new, str) and new and new[0] in '{[':
            try:
                new = json.loads(new)
            except:
                pass
        
        # Compare values
        if curr != new:
            return True
    
    return False


def sync_db_to_excel(sheet_name: str = "Inventory") -> Dict[str, Any]:
    """
    Sync data from JSON files back to Excel.
    Only updates cells where there are changes.
    
    Args:
        sheet_name: Name of the Excel sheet to update
    
    Returns:
        Dict with sync statistics
    """
    try:
        # Load Excel file
        excel_file = config.INVENTORY_FILE_PATH
        if not excel_file.exists():
            return {"success": False, "message": f"Excel file not found: {excel_file}"}
        
        # Read current Excel data
        df = pd.read_excel(excel_file, sheet_name=sheet_name)
        
        # Track changes
        changes_made = 0
        rows_processed = 0
        columns_updated = set()
        
        # Load workbook for direct cell editing
        wb = load_workbook(excel_file)
        ws = wb[sheet_name]
        
        # Get header row (first row)
        headers = {cell.value: idx + 1 for idx, cell in enumerate(ws[1])}
        
        # Columns to update
        columns_to_update = EXCEL_COLUMNS_TO_SYNC
        
        # Find rows by SKU and update
        sku_col = None
        for col_name, col_idx in headers.items():
            if col_name and "sku" in str(col_name).lower() and "old" in str(col_name).lower():
                sku_col = col_idx
                break
        
        if not sku_col:
            return {"success": False, "message": "Could not find SKU column in Excel"}
        
        # Process each row
        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=False), start=2):
            sku_cell = ws.cell(row=row_idx, column=sku_col)
            sku = sku_cell.value
            
            if not sku:
                continue
            
            rows_processed += 1
            
            # Get JSON data for this SKU
            json_values = flatten_json_sections(str(sku))
            
            if not json_values:
                continue
            
            # Update cells where there are changes
            for col_name in columns_to_update:
                if col_name not in headers:
                    continue
                
                col_idx = headers[col_name]
                current_cell = ws.cell(row=row_idx, column=col_idx)
                current_value = current_cell.value
                new_value = json_values.get(col_name)
                
                # Convert new value to appropriate format for Excel
                if isinstance(new_value, dict):
                    new_value = json.dumps(new_value, ensure_ascii=False)
                elif isinstance(new_value, (list, tuple)):
                    new_value = json.dumps(new_value, ensure_ascii=False)
                
                # Detect changes
                if detect_changes({col_name: current_value}, {col_name: new_value}):
                    current_cell.value = new_value
                    changes_made += 1
                    columns_updated.add(col_name)
        
        # Save workbook
        wb.save(excel_file)
        
        return {
            "success": True,
            "message": f"Successfully synced {rows_processed} rows from JSON to Excel",
            "stats": {
                "rows_processed": rows_processed,
                "changes_made": changes_made,
                "columns_updated": sorted(list(columns_updated))
            }
        }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"Error during sync: {str(e)}"
        }
