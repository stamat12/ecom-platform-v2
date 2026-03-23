# Total Cost Net Automation - Implementation Summary

## Overview
Implemented automatic calculation and management of the **Total Cost Net** column in the inventory database. Total Cost Net is calculated as: **Price Net + Shipping Net**.

All three columns are now automatically:
- Coerced to float values with 2 decimal places
- Properly formatted when synced to/from Excel
- Calculated automatically on import/update

## Problem Analysis

### Issues with Previous Implementation:
1. **Empty Values:** Most Total Cost Net values were empty in the database even though Price Net and Shipping Net were available
2. **No Automation:** When new SKUs were imported from Excel, Total Cost Net wasn't being calculated
3. **Text Format:** Financial columns were sometimes stored as text instead of numeric floats
4. **Locale Issues:** Values with comma decimal separators (European format) weren't being properly converted
5. **No Sync:** The db-to-excel sync wasn't including these financial columns

## Solution Implementation

### Modified Files:

#### 1. **backend/app/services/excel_to_db_sync.py**
Added automatic calculation and coercion when importing from Excel:

**New Helper Functions:**
- `_coerce_to_float_2digits(value)` - Converts any value to float with 2 decimal places
  - Handles comma decimal separators (European format: "12,34" → 12.34)
  - Handles None/NaN values gracefully
  - Rounds to exactly 2 decimal places
  
- `_calculate_total_cost_net(price_net, shipping_net)` - Calculates Total Cost Net
  - Coerces both inputs to float
  - Returns None if either input is missing (with warning log)
  - Rounds result to 2 decimal places

**Updated Functions:**
- `add_missing_sku_rows_from_excel()` - Now calculates Total Cost Net when inserting new SKUs
- `sync_excel_to_db()` - Now calculates Total Cost Net in all three sync modes:
  - FULL REPLACE mode (deletes and re-inserts all rows)
  - UPDATE mode (selectively updates existing rows)
  - INSERT mode (adds new rows for other sheets)

**Applied To All Financial Columns:**
- Price Net
- Shipping Net
- Total Cost Net
- OP (already was being coerced)

#### 2. **backend/app/services/inventory_json_db_importer.py**
Added automatic calculation when importing from product JSON files:

**New Helper Functions:**
- Same `_coerce_to_float_2digits()` and `_calculate_total_cost_net()` functions

**Updated Functions:**
- `update_db_from_jsons()` - Now coerces financial columns and calculates Total Cost Net for both updates and inserts

#### 3. **backend/app/services/db_to_excel_sync.py**
Enhanced Excel export functionality:

**Updated Functions:**
- `_coerce_excel_value()` - Extended to handle all financial columns (was only handling OP)
  - Now coerces: OP, Price Net, Shipping Net, Total Cost Net
  - All written as floats with 2 decimal places

**Updated Column List:**
- Added "Price Net", "Shipping Net", "Total Cost Net" to `EXCEL_COLUMNS_TO_SYNC`
- These values now flow back from database to Excel on every sync

### New Script:

#### **backend/scripts/backfill_inventory_total_cost_net.py**
Manual backfill script to calculate Total Cost Net for existing records:

```bash
# Dry run (report what would change without modifying DB)
python backend/scripts/backfill_inventory_total_cost_net.py --dry-run

# Backfill missing Total Cost Net values
python backend/scripts/backfill_inventory_total_cost_net.py

# Force recalculation for all records
python backend/scripts/backfill_inventory_total_cost_net.py --force
```

## Data Flow

### When Adding New SKUs from Excel:
```
Excel Row (Price Net, Shipping Net)
    ↓
excel_to_db_sync.add_missing_sku_rows_from_excel()
    ↓
_coerce_to_float_2digits() applied to each  
    ↓
_calculate_total_cost_net() = Price Net + Shipping Net
    ↓
Database (all 3 columns as float, 2 decimal places)
```

### When Syncing Excel to Database:
```
Excel Sheet (Price Net, Shipping Net)
    ↓
sync_excel_to_db()
    ↓
_coerce_to_float_2digits() applied
    ↓
_calculate_total_cost_net() if either Price/Shipping updated
    ↓
Database UPDATE (all as float, 2 decimal places)
```

### When Syncing Database to Excel:
```
Database (Price Net, Shipping Net, Total Cost Net)
    ↓
db_to_excel_sync (now includes financial columns)
    ↓
_coerce_excel_value() written as numeric Excel cells
    ↓
Excel (displayed as proper float numbers, not text)
```

### When Importing from JSON:
```
Product JSON File
    ↓
inventory_json_db_importer.update_db_from_jsons()
    ↓
_coerce_to_float_2digits() applied
    ↓
_calculate_total_cost_net() if Price/Shipping present
    ↓
Database UPDATE/INSERT
```

## Key Features

### 1. **Automatic Calculation**
- Total Cost Net is **automatically calculated** whenever Price Net or Shipping Net are imported/updated
- No manual intervention needed for new SKUs

### 2. **Float Formatting (2 Decimal Places)**
- All financial columns stored as proper floats: `12.34` not `"12.34"` or `"12,34"`
- Excel displays them as numbers with proper formatting
- Calculations are mathematically accurate

### 3. **Locale Handling**
- Handles European decimal format: `12,34` → `12.34`
- Handles standard decimal format: `12.34` → `12.34`
- Works with any source (Excel, JSON, API)

### 4. **Error Handling**
- Missing or invalid values handled gracefully with warning logs
- If either Price Net or Shipping Net is missing/invalid, Total Cost Net remains empty with warning
- Script continues processing other rows

### 5. **Idempotent Operations**
- Can re-run calculations without data corruption
- Detecting existing Total Cost Net prevents recalculation (unless --force used)
- Safe for production use

## Configuration

All column names reference **config.py**:
```python
PRICE_NET_COLUMN = "Price Net"
SHIPPING_NET_COLUMN = "Shipping Net"  
TOTAL_COST_NET_COLUMN = "Total Cost Net"
OP_COLUMN = "OP"
```

If column names change in your config, the automation automatically adapts.

## Implementation Checklist

- [x] Add helper functions for float coercion and calculation
- [x] Update `excel_to_db_sync.py` (all three sync modes)
- [x] Update `inventory_json_db_importer.py`
- [x] Update `db_to_excel_sync.py` (export + column list)
- [x] Create backfill script
- [x] Handle European decimal format (comma separator)
- [x] Ensure all financial columns are floats
- [x] Test for syntax errors

## Deployment Steps

1. **Restart Backend Server**
   ```bash
   # In your backend terminal, restart uvicorn
   uvicorn app.main:app --reload
   ```

2. **Backfill Existing Data (One-Time)**
   ```bash
   # First, dry run to see what would change
   python backend/scripts/backfill_inventory_total_cost_net.py --dry-run
   
   # Then backfill
   python backend/scripts/backfill_inventory_total_cost_net.py
   ```

3. **Verify Results**
   - Open inventory.db and check a few SKUs
   - Total Cost Net should now have values = Price Net + Shipping Net
   - All values should be numeric floats, not text
   - In Excel, they should display right-aligned (numbers), not left-aligned (text)

## Testing

### Test Case 1: New SKU Import
- Add a new row to Excel with:
  - Price Net: 12.34
  - Shipping Net: 5.66
- Run: Import new SKUs
- Expected: Database should have Total Cost Net = 18.00

### Test Case 2: Update Existing
- Change Price Net from 12.34 to 20.00 for a SKU with Shipping Net 5.66
- Run: Sync Excel to DB
- Expected: Total Cost Net automatically updated to 25.66

### Test Case 3: Locale Format
- Add to Excel: Price Net = "12,50" (comma separator)
- Import
- Expected: Database stores as 12.50 (float)

### Test Case 4: Excel Roundtrip
- Sync DB to Excel
- Open Excel file
- Check Total Cost Net column values
- Expected: Shows as numbers (right-aligned), not text (left-aligned)

## Troubleshooting

### Q: Why are my values still empty?
**A:** Run the backfill script to process existing records:
```bash
python backend/scripts/backfill_inventory_total_cost_net.py
```

### Q: Values appear as text in Excel (left-aligned)?
**A:** Sync the database back to Excel using the db_to_excel_sync service. The `_coerce_excel_value()` function will write them as proper numeric cells.

### Q: Some rows show warnings about missing Price/Shipping Net
**A:** This is expected. Those rows cannot calculate Total Cost Net without both inputs. Verify the source data to ensure Price Net and Shipping Net are populated.

## Performance Impact

- **Minimal:** Only affects import/sync operations
- **No Database Migration Needed:** Uses existing columns
- **Backward Compatible:** Doesn't break existing code or data

## Future Enhancements

Possible future improvements:
- [ ] API endpoint to manually recalculate Total Cost Net
- [ ] UI indicator for rows needing calculation
- [ ] Batch operation in UI to fix multiple SKUs
- [ ] Audit log for Total Cost Net changes
