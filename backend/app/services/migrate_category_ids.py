"""Migration script to add missing eBay Category IDs to all product JSONs.

This script finds all product JSON files that have a Category path but are
missing the eBay Category ID, looks up the ID from category_mapping.json,
and adds it to the JSON.
"""
import json
from pathlib import Path
from typing import Dict, List, Tuple

# Import the category lookup function
from .json_generation import get_category_id_for_path


def migrate_all_category_ids() -> Tuple[int, int, int]:
    """Migrate all product JSONs to add missing Category IDs.
    
    Returns:
        Tuple of (total_files, updated_files, errors)
    """
    products_dir = Path(__file__).resolve().parents[2] / "legacy" / "products"
    
    total_files = 0
    updated_files = 0
    errors = 0
    
    print(f"\n[MIGRATION] Starting Category ID migration in: {products_dir}")
    print("=" * 80)
    
    if not products_dir.exists():
        print(f"[ERROR] Products directory not found: {products_dir}")
        return 0, 0, 1
    
    json_files = sorted(products_dir.glob("*.json"))
    print(f"[MIGRATION] Found {len(json_files)} JSON files")
    
    for json_file in json_files:
        total_files += 1
        sku = json_file.stem
        
        try:
            # Load JSON
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Get SKU data (handle single or multi-SKU format)
            sku_data = data.get(sku, {})
            if not sku_data:
                # Try to find first key
                for key, val in data.items():
                    if isinstance(val, dict):
                        sku_data = val
                        break
            
            if not sku_data:
                print(f"[SKIP] {sku}: No SKU data found")
                continue
            
            # Check Ebay Category section
            ebay_cat = sku_data.get("Ebay Category", {})
            if not isinstance(ebay_cat, dict):
                print(f"[SKIP] {sku}: Ebay Category is not a dict")
                continue
            
            category_path = ebay_cat.get("Category", "")
            category_id = ebay_cat.get("eBay Category ID", "")
            
            # Skip if both exist
            if category_path and category_id:
                print(f"[OK]   {sku}: Category ID already present")
                continue
            
            # Skip if no category path
            if not category_path:
                print(f"[SKIP] {sku}: No Category path found")
                continue
            
            # Look up the category ID
            looked_up_id = get_category_id_for_path(category_path)
            
            if looked_up_id:
                # Add it to the JSON
                data[sku]["Ebay Category"]["eBay Category ID"] = looked_up_id
                
                # Write back
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                print(f"[ADD]  {sku}: Added Category ID {looked_up_id}")
                updated_files += 1
            else:
                print(f"[MISS] {sku}: Category path not found in mapping: {category_path[:60]}...")
        
        except json.JSONDecodeError as e:
            print(f"[ERR]  {sku}: JSON decode error: {e}")
            errors += 1
        except Exception as e:
            print(f"[ERR]  {sku}: {type(e).__name__}: {e}")
            errors += 1
    
    print("=" * 80)
    print(f"[MIGRATION COMPLETE]")
    print(f"  Total files:    {total_files}")
    print(f"  Updated files:  {updated_files}")
    print(f"  Errors:         {errors}")
    print()
    
    return total_files, updated_files, errors


if __name__ == "__main__":
    migrate_all_category_ids()
