# Per-Column Advanced Filtering System

## Overview
A comprehensive advanced filtering system has been implemented that allows users to filter eBay listings by individual columns with type-aware controls. This replaces the limited global filter approach with flexible, per-column filtering.

## Features

### 1. **Smart Filter Types** (Auto-detected by column)
- **Text Search**: Simple substring search (case-insensitive)
  - Applied to: SKU, Title, Condition, Category, Link, and all SEO fields
  - Example: Filter SKU by "HAN" to find all HANDEL items
  
- **Numeric Range**: Min/Max numeric bounds
  - Applied to: Price, Quantities, Profit values, Commission, Costs, Count Main Images
  - Example: Filter Price €: Min 20, Max 100
  
- **Date Range**: From/To date selectors
  - Applied to: Start Time, End Time
  - Example: Filter listings created between 2025-01-01 and 2025-02-28
  
- **Boolean**: True/False/Any dropdown
  - Applied to: Best Offer Enabled
  - Example: Show only listings with Best Offer enabled

### 2. **User Interface**

#### Advanced Filters Button
- Orange button with 🔍 icon in the control bar
- Shows count badge of active filters: "🔍 Advanced Filters (3)"
- Distinct from the old basic filters (now grayed out)

#### Filter Modal
- Large modal dialog (max-width: 800px)
- **Scrollable list** of all visible columns
- **Expandable sections** - click column name to expand/collapse
- **Quick visual indicators**:
  - Blue checkbox ✓ shows which columns have active filters
  - Blue left border on filtered columns
  
#### Filter Controls
- **Text fields**: Type to search (real-time, no submit needed)
- **Number inputs**: Min/Max fields with live validation
- **Date fields**: HTML5 date selectors with range support
- **Select dropdowns**: Boolean choices

#### Action Buttons
- **Reset All**: Clear all filters at once
- **Apply Filters**: Count shows how many columns are filtered
- **Clear Filter**: Per-column button to remove that column's filter
- **X (Close)**: Cancel without applying

### 3. **Data Persistence**
- All column filters saved to localStorage: `ebayListingsColumnFilters`
- Persists across page reloads
- Automatically cleared when user clicks "Reset All"

### 4. **Backend Integration**

#### API Parameter
```
column_filters=[JSON] - Stringified JSON object with filter definitions
```

Example:
```json
{
  "sku": {"text": "HAN"},
  "price": {"min": 20, "max": 100},
  "profit.net_profit_margin_percent": {"min": 50},
  "start_time": {"from": "2025-02-01", "to": "2025-03-31"},
  "best_offer_enabled": {"value": true}
}
```

#### Filter Processing
- Filters are applied sequentially to listings
- Empty/null filters are skipped (no performance penalty)
- Supports nested fields (e.g., `profit.net_profit_margin_percent`)
- Handles missing fields gracefully (treats as 0 for numeric, empty string for text)

#### Tested Filter Operations
✅ Text search on string fields
✅ Data range queries on numeric fields
✅ Nested field access (dot notation)
✅ Date range filtering
✅ Boolean value matching
✅ Multi-column simultaneous filtering
✅ Empty filter cases

## Usage Examples

### Example 1: Find profitable HANDEL items
1. Click "🔍 Advanced Filters"
2. SKU → type "HAN"
3. Profit % → Min: 50
4. Click "Apply Filters"
→ Shows only HANDEL listings with >50% profit margin

### Example 2: Filter recent, low-priced items
1. Click "🔍 Advanced Filters"
2. Size Price € → Min: 5, Max: 25
3. Start Time → From: 2025-02-01
4. Click "Apply Filters"
→ Shows affordable items listed in February 2025

### Example 3: Best Offer items only
1. Click "🔍 Advanced Filters"
2. Best Offer → Toggle to "True / Yes"
3. Click "Apply Filters"
→ Shows only listings where customers can make offers

## Technical Implementation

### Frontend (`AdvancedFilters.jsx`)
- React component with expandable column list
- Smart column type detection (text/number/date/boolean)
- Per-column filter state management
- localStorage persistence

### Backend (`main.py`)
- Added `column_filters` parameter to `/api/ebay-cache/de-listings`
- Implemented `get_field_value()` helper for nested field access
- Sequential filter application with type-aware comparisons
- No changes to existing filters - backward compatible

## File Changes

### Created
- `frontend/src/components/AdvancedFilters.jsx` (230+ lines)

### Modified
- `frontend/src/pages/EbayListingsCachePage.jsx`:
  - Imported AdvancedFilters component
  - Added `showAdvancedFilters` state
  - Added `columnFilters` state (localStorage sync)
  - Updated `fetchListings()` to include `column_filters` parameter
  - Added Advanced Filters button with active filter count
  - Integrated AdvancedFilters modal

- `backend/app/main.py`:
  - Added `column_filters` parameter to GET endpoint
  - Implemented per-column filter logic with type detection
  - Added nested field value extraction
  - Supports text, numeric range, date range, and boolean filters

## Browser Compatibility
- Works in all modern browsers (Chrome, Firefox, Safari, Edge)
- Uses HTML5 date inputs (graceful fallback to text in unsupported browsers)
- localStorage for persistence
- No external filter libraries required

## Performance Notes
- Filters applied in-memory before pagination
- Empty filters skipped (zero overhead)
- Results count shown before rendering
- Pagination resets to page 1 on new filters

## Future Enhancements
- Multi-select for categorical fields (listing_type, condition_name, marketplace)
- Regex support for advanced text search
- Filter presets/saved searches
- Export/import filter configurations
- Filter by null/empty values
- Case-sensitive search toggle
