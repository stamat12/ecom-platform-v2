"""
Generate category_mapping.json from Excel "Ebay Categories" sheet with all columns including fees.
"""
import pandas as pd
import json
from pathlib import Path

# Paths
INVENTORY_FILE = r"C:\Users\stame\OneDrive\TRADING_SEGMENT\Inventory.xlsx"
OUTPUT_FILE = Path(__file__).parent.parent / "schemas" / "category_mapping.json"

# Column names from the Excel sheet
CATEGORY_TITLE_COLUMN = "Category"
CATEGORY_ID_COLUMN = "ID"
PAYMENT_FEE_COLUMN = "Payment Fee"
FINAL_AMOUNT_UP_TO_COLUMN = "Up To"
SALES_COMMISSION_UP_TO_COLUMN = "Sales commission per item Up To"
FINAL_AMOUNT_FROM_COLUMN = "From"
SALES_COMMISSION_FROM_COLUMN = "Sales commission per item From"

def main():
    print(f"Reading Excel file: {INVENTORY_FILE}")
    
    # Read the "Ebay Categories" sheet
    df = pd.read_excel(INVENTORY_FILE, sheet_name="Ebay Categories")
    
    print(f"Found {len(df)} categories in Excel sheet")
    print(f"Columns: {list(df.columns)}")
    
    # Create category mappings with all data
    category_mappings = []
    
    for _, row in df.iterrows():
        category = str(row[CATEGORY_TITLE_COLUMN]).strip() if pd.notna(row[CATEGORY_TITLE_COLUMN]) else ""
        category_id = str(row[CATEGORY_ID_COLUMN]).strip() if pd.notna(row[CATEGORY_ID_COLUMN]) else ""
        
        if not category or not category_id:
            continue
        
        # Extract fee data
        payment_fee = row[PAYMENT_FEE_COLUMN] if pd.notna(row[PAYMENT_FEE_COLUMN]) else 0.35
        final_amount_up_to = row[FINAL_AMOUNT_UP_TO_COLUMN] if pd.notna(row[FINAL_AMOUNT_UP_TO_COLUMN]) else None
        sales_commission_up_to = row[SALES_COMMISSION_UP_TO_COLUMN] if pd.notna(row[SALES_COMMISSION_UP_TO_COLUMN]) else None
        final_amount_from = row[FINAL_AMOUNT_FROM_COLUMN] if pd.notna(row[FINAL_AMOUNT_FROM_COLUMN]) else None
        sales_commission_from = row[SALES_COMMISSION_FROM_COLUMN] if pd.notna(row[SALES_COMMISSION_FROM_COLUMN]) else None
        
        mapping = {
            "categoryName": category.split("/")[-1].strip() if "/" in category else category,
            "categoryId": category_id,
            "fullPath": category,
            "market": "EBAY_DE",
            "fees": {
                "payment_fee": float(payment_fee),
                "final_amount_up_to": float(final_amount_up_to) if final_amount_up_to is not None else None,
                "sales_commission_up_to": float(sales_commission_up_to) if sales_commission_up_to is not None else None,
                "final_amount_from": float(final_amount_from) if final_amount_from is not None else None,
                "sales_commission_from": float(sales_commission_from) if sales_commission_from is not None else None
            }
        }
        
        category_mappings.append(mapping)
    
    # Create final structure
    output_data = {
        "categoryMappings": category_mappings
    }
    
    # Save to JSON file
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nSaved {len(category_mappings)} category mappings to {OUTPUT_FILE}")
    print(f"File size: {OUTPUT_FILE.stat().st_size:,} bytes")
    
    # Show sample
    if category_mappings:
        print("\nSample mapping:")
        print(json.dumps(category_mappings[0], indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
