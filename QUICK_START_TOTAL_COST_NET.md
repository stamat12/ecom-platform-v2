# Total Cost Net Automation - Quick Start Guide

## What Was Done

I've implemented **automatic calculation and formatting** of the Total Cost Net column in your inventory database. 

### The Problem (What You Told Me):
- ❌ Total Cost Net values are empty even though Price Net and Shipping Net are in Excel
- ❌ When you import new SKUs from Excel, Total Cost Net isn't being calculated
- ❌ Financial columns are stored as text instead of numeric floats with 2 decimal places

### The Solution:
- ✅ **Automatic Calculation:** Total Cost Net = Price Net + Shipping Net
- ✅ **All Entry Points:** Works when importing from Excel, JSON, and database syncs
- ✅ **Proper Formatting:** All 3 columns stored as floats with exactly 2 decimal places
- ✅ **European Format:** Handles comma decimal separators (12,34 → 12.34)

## Files Modified

### 1. `backend/app/services/excel_to_db_sync.py` ✅
- Added `_coerce_to_float_2digits()` - converts values to float with 2 decimal places  
- Added `_calculate_total_cost_net()` - calculates the sum
- Updated `add_missing_sku_rows_from_excel()` - calculates when adding new SKUs
- Updated `sync_excel_to_db()` - calculates when updating ALL sync modes

### 2. `backend/app/services/inventory_json_db_importer.py` ✅
- Added same helper functions
- Updated `update_db_from_jsons()` - calculates when importing from JSON files

### 3. `backend/app/services/db_to_excel_sync.py` ✅
- Updated `_coerce_excel_value()` - now formats Price Net, Shipping Net, Total Cost Net
- Added financial columns to sync list (they now flow back to Excel)

### 4. `backend/scripts/backfill_inventory_total_cost_net.py` ✅ (NEW)
- One-time backfill script for existing data
- Can recalculate all records if needed

### 5. `TOTAL_COST_NET_AUTOMATION.md` ✅ (NEW)
- Complete technical documentation

## How to Use It

### Step 1: Restart Backend Server
```powershell
# Stop current uvicorn (Ctrl+C in the terminal)
# Then restart it:
uvicorn app.main:app --reload
```

### Step 2: Backfill Existing Data (One-Time)
```powershell
cd c:\Users\stame\OneDrive\TRADING_SEGMENT\ecom-platform-v2

# Dry run first (see what will change without doing it)
python backend/scripts/backfill_inventory_total_cost_net.py --dry-run

# Then actually do it
python backend/scripts/backfill_inventory_total_cost_net.py
```

### Step 3: Test It
1. Add a new row to Excel with:
   - SKU: TEST123
   - Price Net: 10.00
   - Shipping Net: 5.50
   
2. Import the SKUs

3. Check the database - Total Cost Net should be **15.50**

## What Happens Now (Automatically)

### When You Import New SKUs from Excel:
```
Excel: Price Net=12.34, Shipping Net=5.66
    ↓
Auto-calculated: Total Cost Net = 18.00
    ↓
Saved to DB as float values with 2 decimals
```

### When You Update Prices in Excel:
```
Excel: Changed Price Net from 12 to 20, Shipping Net = 5
    ↓
Auto-recalculated: Total Cost Net = 25.00
    ↓
Saved to DB
```

### When You Sync DB Back to Excel:
```
DB: Price Net=12.34, Shipping Net=5.66, Total Cost Net=18.00
    ↓
Written to Excel as proper numeric columns (not text)
    ↓
Shows right-aligned in Excel (numbers, not text)
```

## All Financial Columns Now Get This Treatment

✅ **Price Net** - Coerced to float with 2 decimal places
✅ **Shipping Net** - Coerced to float with 2 decimal places  
✅ **Total Cost Net** - Calculated automatically as sum
✅ **OP** - Also coerced (was already partially handled)

## Key Features

| Feature | Before | After |
|---------|--------|-------|
| Total Cost Net when importing | ❌ Empty | ✅ Calculated automatically |
| Format in Excel | ❌ Text (left-aligned) | ✅ Numbers (right-aligned) |
| Decimal places | ❌ Inconsistent | ✅ Always exactly 2 |
| European format (12,34) | ❌ Breaks | ✅ Converts to 12.34 |
| Syncs back to Excel | ❌ No | ✅ Yes |
| Works with new SKUs | ❌ Manual calculation | ✅ Automatic |

## Verification Checklist

After running the backfill script, verify:

- [ ] Open `inventory.db` in a SQL tool
- [ ] Check a few SKUs: Total Cost Net should equal Price Net + Shipping Net
- [ ] Values should be floats like `12.34`, not text like `"12.34"`
- [ ] No NULL values for Total Cost Net (where Price & Shipping exist)
- [ ] In Excel: Financial columns should display right-aligned (numbers not text)

## If Something Goes Wrong

### "Total Cost Net is still empty"
→ Run the backfill script (Step 2 above)

### "Values still show as text in Excel"
→ Use db_to_excel_sync to re-export from database

### "Some rows show warnings about missing data"
→ Check those SKUs in Excel - they're missing Price Net or Shipping Net

## No Breaking Changes

✅ **Safe to deploy** - Backward compatible with existing code
✅ **No database migration** - Uses existing columns
✅ **No data loss** - Only calculates/formats, doesn't delete anything

---

Questions? The detailed documentation is in:
`ecom-platform-v2/TOTAL_COST_NET_AUTOMATION.md`
