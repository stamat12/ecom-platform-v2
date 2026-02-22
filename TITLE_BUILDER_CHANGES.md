# eBay Title Builder Restructuring - Summary

## Changes Made

### 1. **Function:** `build_title_from_product()` 
**File:** [backend/app/services/ebay_listing.py](backend/app/services/ebay_listing.py#L683)

#### Old Logic
```
Brand + Keywords + Color + "Größe {Size}"
Max 80 chars (with simple optimization)
```

#### New Logic
```
Brand + Model + Product Type + Gender (translated) + Color + Size + Keyword 1 + Keyword 2 + Keyword 3 + Condition
Max 80 chars with priority-based cascade truncation
```

### 2. **Component Order** (Exact sequence)
1. Brand
2. Product Model
3. Product Type
4. Gender (translated from code)
5. Color
6. Size
7. Keyword 1
8. Keyword 2
9. Keyword 3
10. Condition

### 3. **Gender Code Mapping**
| Code | Translation |
|------|------------|
| M | Herren |
| F | Damen |
| U | Unisex |
| KB | Jungen |
| KG | Mädchen |
| KU | Kinder Unisex |

### 4. **Data Sources**
- **Brand, Gender, Color, Size** → `Intern Product Info`
- **Model, Product Type, Keyword 1-3** → `eBay SEO`
- **Condition** → `Product Condition`

### 5. **Truncation Cascade (Priority-based)**
If title > 80 chars:
1. **Stage 1:** Remove `Condition` (lowest priority)
2. **Stage 2:** Remove `Keyword 3` (if still > 80 chars)
3. **Stage 3:** Remove `Keyword 2` (if still > 80 chars)
4. **Stage 4:** Raise `ValueError` with details (if still > 80 chars)

Error message format:
```
Title exceeds 80 chars for SKU {sku} even after removing Condition, 
Keyword 3, and Keyword 2. Current: {title} ({length} chars)
```

### 6. **Backward Compatibility**
- All components are optional except `Product Type` (required)
- Missing optional components are simply omitted from the title
- If `Product Type` is missing → raises clear error
- Components are separated by spaces in the final title

### 7. **Validation Results**
✅ **TEST 1:** Full title construction with all components fits in 80 chars
```
Hunkemöller Lotta Bügel-BH Damen Schwarz 80B Push-Up-BH Gepolsterter BH Damen BH
(80 chars)
```

✅ **TEST 2:** Gender code translations (M → Herren, F → Damen, U → Unisex)

✅ **TEST 3:** Missing `Product Type` correctly raises error

✅ **TEST 4:** Backend imports successfully with changes

### 8. **Integration Points**
- Called by: `create_listing()` at [line 858](backend/app/services/ebay_listing.py#L858)
- Used in: XML listing request with `html.escape(title)` at [line 976](backend/app/services/ebay_listing.py#L976)
- Passed to: `build_description_html()` for potential use in description

### 9. **Error Handling**
Two error scenarios:
1. **Missing Product Type** → ValueError with missing field indicator
2. **Title exceeds 80 chars after all truncation** → ValueError with current title and length

This allows manual intervention for SKUs with genuinely long product names.

## Testing Notes

All test scenarios passed:
- ✓ Full title construction
- ✓ Gender code translation
- ✓ Error on missing Product Type
- ✓ Backend import validation
- ✓ XML integration (html.escape compatibility)

## Next Steps

When adding SEO enrichment to existing products (HAN000350.json, etc.):
1. Populate `eBay SEO` section with:
   - `Product Model`
   - `Product Type` (required)
   - `Keyword 1`, `Keyword 2`, `Keyword 3`
2. Ensure `Product Condition` field is set
3. Test title generation via API or direct function call
4. Address any titles that exceed 80 chars after truncation cascade
