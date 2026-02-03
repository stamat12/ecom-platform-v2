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

# JSON sections to sync
JSON_SECTIONS_TO_SYNC = [
    "Ebay Category",
    "EAN",
    "Product Condition",
    "Intern Product Info",
    "Intern Generated Info",
    "OP",
    "Status",
    "Warehouse"
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


def get_image_counts(sku: str) -> Dict[str, int]:
    """Extract image counts from JSON."""
    json_data = read_sku_json(sku)
    if not json_data:
        return {"Json Phone stock": 0, "Json Enhanced": 0}
    
    images = json_data.get("Images", {})
    summary = images.get("summary", {})
    
    return {
        "Json Phone stock": summary.get("count_phone", 0),
        "Json Enhanced": summary.get("count_enhanced", 0)
    }


def flatten_json_sections(sku: str) -> Dict[str, Any]:
    """Flatten JSON sections into a single dict for Excel columns."""
    json_data = read_sku_json(sku)
    if not json_data:
        return {}
    
    flattened = {}
    
    # Map section names to their main content field
    section_mappings = {
        "Ebay Category": lambda x: x.get("eBay Category ID"),
        "EAN": lambda x: x.get("EAN"),
        "Product Condition": lambda x: x.get("Condition"),
        "Intern Product Info": lambda x: json.dumps(x),
        "Intern Generated Info": lambda x: json.dumps(x),
        "OP": lambda x: x.get("OP"),
        "Status": lambda x: x.get("Status"),
        "Warehouse": lambda x: x.get("Lager"),
    }
    
    for section_name, extractor in section_mappings.items():
        section_data = json_data.get(section_name)
        if section_data:
            try:
                flattened[section_name] = extractor(section_data)
            except Exception as e:
                print(f"Error extracting {section_name} for {sku}: {e}")
                flattened[section_name] = None
    
    # Add image counts
    image_counts = get_image_counts(sku)
    flattened.update(image_counts)
    
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
        columns_to_update = JSON_SECTIONS_TO_SYNC + ["Json Phone stock", "Json Enhanced"]
        
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
