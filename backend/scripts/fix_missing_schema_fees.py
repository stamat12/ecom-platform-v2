#!/usr/bin/env python
"""
Analyzes schema JSON files in the schemas folder and adds missing fees from category_mapping.json.

Logs which categories have null/missing fees in the mapping.
"""
import json
from pathlib import Path
from datetime import datetime

schemas_dir = Path(__file__).parent.parent / "schemas"
mapping_file = schemas_dir / "category_mapping.json"
log_file = Path(__file__).parent.parent / "logs" / "schema_fees_analysis.log"

# Create logs directory
log_file.parent.mkdir(parents=True, exist_ok=True)


def log_message(msg: str, print_also: bool = True):
    """Write message to log file."""
    if print_also:
        print(msg)
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(msg + "\n")


def main():
    # Clear previous log
    log_file.write_text("")
    
    log_message("=" * 70)
    log_message(f"Schema Fees Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log_message("=" * 70)
    
    # Load category mapping
    log_message("\n📖 Loading category mapping...")
    if not mapping_file.exists():
        log_message(f"❌ Category mapping file not found: {mapping_file}")
        return
    
    try:
        with open(mapping_file, 'r', encoding='utf-8') as f:
            mapping_data = json.load(f)
        log_message(f"✅ Loaded category mapping with {len(mapping_data.get('categoryMappings', []))} categories")
    except Exception as e:
        log_message(f"❌ Error loading mapping: {e}")
        return
    
    # Create lookup dict by category ID
    category_mapping = {}
    for cat in mapping_data.get('categoryMappings', []):
        cat_id = str(cat.get('categoryId', ''))
        category_mapping[cat_id] = cat
    
    log_message(f"   Created lookup for {len(category_mapping)} categories")
    
    # Find all schema files
    log_message("\n📁 Scanning schema folder...")
    schema_files = list(schemas_dir.glob("EbayCat_*.json"))
    log_message(f"   Found {len(schema_files)} schema files")
    
    if not schema_files:
        log_message("   ❌ No schema files found!")
        return
    
    # Analyze and fix each schema
    log_message("\n" + "=" * 70)
    log_message("ANALYSIS RESULTS")
    log_message("=" * 70)
    
    missing_fees_count = 0
    null_fees_categories = []
    fixed_count = 0
    error_count = 0
    
    for schema_file in sorted(schema_files):
        try:
            with open(schema_file, 'r', encoding='utf-8') as f:
                schema_data = json.load(f)
            
            # Extract category ID from filename
            # Format: EbayCat_{category_id}_EBAY_DE.json
            parts = schema_file.stem.split('_')
            if len(parts) >= 2:
                cat_id = parts[1]
            else:
                log_message(f"   ⚠️  Could not parse category ID from {schema_file.name}")
                continue
            
            # Check metadata
            metadata = schema_data.get('_metadata', {})
            fees = metadata.get('fees', {})
            
            # Check if fees exist and are not empty
            has_fees = fees and (fees.get('payment_fee') is not None or fees.get('sales_commission_percentage') is not None)
            
            if not has_fees:
                missing_fees_count += 1
                log_message(f"\n📋 {schema_file.name}")
                log_message(f"   Category ID: {cat_id}")
                log_message(f"   Category: {metadata.get('category_name', 'N/A')}")
                
                # Look up in mapping
                if cat_id in category_mapping:
                    cat_mapping = category_mapping[cat_id]
                    mapping_fees = cat_mapping.get('fees', {})
                    payment_fee = mapping_fees.get('payment_fee')
                    sales_commission = mapping_fees.get('sales_commission_up_to')
                    
                    log_message(f"   ✅ Found in mapping:")
                    log_message(f"      - Payment Fee: €{payment_fee if payment_fee is not None else 'NULL'}")
                    log_message(f"      - Sales Commission: {sales_commission if sales_commission is not None else 'NULL'}%")
                    
                    # Check if we can add the fees
                    if payment_fee is not None or sales_commission is not None:
                        # Update schema with fees
                        new_fees = {
                            'payment_fee': float(payment_fee) if payment_fee is not None else 0.0,
                            'sales_commission_percentage': float(sales_commission) if sales_commission is not None else 0.0
                        }
                        schema_data['_metadata']['fees'] = new_fees
                        
                        # Write back
                        with open(schema_file, 'w', encoding='utf-8') as f:
                            json.dump(schema_data, f, indent=2, ensure_ascii=False)
                        
                        log_message(f"   ✅ FIXED - Added fees to schema file")
                        fixed_count += 1
                    else:
                        log_message(f"   ❌ MISSING IN MAPPING - Both fees are null in category_mapping!")
                        null_fees_categories.append({
                            'category_id': cat_id,
                            'category_name': metadata.get('category_name', 'N/A'),
                            'file': schema_file.name
                        })
                else:
                    log_message(f"   ❌ NOT FOUND in mapping!")
                    null_fees_categories.append({
                        'category_id': cat_id,
                        'category_name': metadata.get('category_name', 'N/A'),
                        'file': schema_file.name
                    })
        
        except Exception as e:
            error_count += 1
            log_message(f"\n❌ Error processing {schema_file.name}: {e}")
    
    # Summary
    log_message("\n" + "=" * 70)
    log_message("SUMMARY")
    log_message("=" * 70)
    log_message(f"Total schemas scanned: {len(schema_files)}")
    log_message(f"Schemas with missing fees: {missing_fees_count}")
    log_message(f"Successfully fixed: {fixed_count}")
    log_message(f"Errors: {error_count}")
    
    if null_fees_categories:
        log_message(f"\n⚠️  CATEGORIES WITH NULL/MISSING FEES IN MAPPING ({len(null_fees_categories)}):")
        log_message("   Please add these to your Excel 'Ebay Categories' sheet:\n")
        for cat in null_fees_categories:
            log_message(f"   - Category ID: {cat['category_id']}")
            log_message(f"     Name: {cat['category_name']}")
            log_message(f"     File: {cat['file']}\n")
    else:
        log_message("\n✅ All categories have fees in the mapping!")
    
    log_message("\n" + "=" * 70)
    log_message(f"Log saved to: {log_file}")
    log_message("=" * 70)


if __name__ == "__main__":
    main()
