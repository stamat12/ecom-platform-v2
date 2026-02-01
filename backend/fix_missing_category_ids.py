#!/usr/bin/env python3
"""Fix missing eBay Category IDs in JSON files using category_mapping.json"""

import json
from pathlib import Path

# Load category mapping
mapping_file = Path(__file__).parent / "schemas" / "category_mapping.json"
with open(mapping_file, 'r', encoding='utf-8') as f:
    mapping_data = json.load(f)
    mappings = mapping_data.get('categoryMappings', [])

# Create lookup dict: fullPath -> categoryId
category_lookup = {m['fullPath']: str(m['categoryId']) for m in mappings}

print(f"Loaded {len(category_lookup)} category mappings\n")

# The 13 SKUs with missing Category IDs
missing_skus = [
    "VER02176", "VER02177", "VER02178", "VER02179", "VER02180",
    "VER02181", "VER02182", "VER02183", "VER02184", "VER02186",
    "VER02187", "VER02188", "VER02189"
]

products_dir = Path(__file__).parent / "legacy" / "products"
updated_count = 0

for sku in missing_skus:
    json_path = products_dir / f"{sku}.json"
    
    if not json_path.exists():
        print(f"❌ {sku} - File not found")
        continue
    
    try:
        data = json.loads(json_path.read_text(encoding='utf-8'))
        payload = data[sku]
        
        if "Ebay Category" not in payload:
            print(f"⚠️  {sku} - No Ebay Category section")
            continue
        
        category = payload["Ebay Category"].get("Category")
        if not category:
            print(f"⚠️  {sku} - No Category value")
            continue
        
        # Look up category ID
        category_id = category_lookup.get(category)
        if not category_id:
            print(f"❌ {sku} - Category not found in mapping: {category}")
            continue
        
        # Update the JSON
        payload["Ebay Category"]["eBay Category ID"] = category_id
        
        # Save
        json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f"✅ {sku} - Added Category ID: {category_id}")
        updated_count += 1
        
    except Exception as e:
        print(f"❌ {sku} - Error: {e}")

print(f"\n✅ Updated {updated_count}/{len(missing_skus)} files")
