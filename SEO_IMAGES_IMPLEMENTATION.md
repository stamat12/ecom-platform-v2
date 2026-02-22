# SEO Enrichment with Images - Implementation Confirmed

## Summary

Both SEO and eBay enrichment functions now use **main images** for better results.

---

## 1. SEO Enrichment Function (UPDATED ✅)
**Location:** `backend/app/services/ebay_enrichment.py` - `enrich_ebay_seo_fields()`

### What It Does
Generates SEO fields from **both images AND product title**:
- **Product Type** (e.g., "Short", "Dress", "Jacket")
- **Product Model** (e.g., "Model XL-2000")
- **Keyword 1, 2, 3** (searchable keywords)

### How It Works (Updated)
```python
# 1. Load product JSON
product_json = read_sku_json(sku)

# 2. Extract title
title = _extract_title_for_seo(product_json, sku)

# 3. COLLECT MAIN IMAGES (NEW!)
image_paths = _collect_main_image_paths(sku, product_json)

# 4. IF IMAGES FOUND → Use Vision API (NEW!)
if image_paths:
    proposed = _call_openai_vision(
        image_paths,
        EBAY_SEO_ENRICHMENT_PROMPT,
        SEO_FIELD_KEYS  # product_type, keyword_1-3, product_model
    )
# 5. IF NO IMAGES → Fallback to text-based
else:
    proposed = _call_openai_text_json(
        EBAY_SEO_ENRICHMENT_PROMPT,
        "Produkt-Titel:\n" + title + "\n..."
    )

# 6. Merge with existing fields (fill-only mode)
merged = _merge_fill_only_seo(current, proposed)

# 7. Save back to JSON
_write_ebay_seo_fields(product_json, merged)
```

### Vision Prompt (NEW)
When images are available:
```
Produkt-Titel: [TITLE]

Analysiere die Bilder und den Titel um folgende SEO-Felder auszufüllen:
- product_type: Art des Produkts (z.B. 'Short', 'Dress', 'Jacket')
- product_model: Modellnummer oder spezifisches Modell (falls sichtbar)
- keyword_1, keyword_2, keyword_3: Relevante Suchbegriffe für dieses Produkt

Liefere ausschließlich JSON mit genau diesen Keys: 
product_type, product_model, keyword_1, keyword_2, keyword_3
```

### Fallback
If no images found → Uses text-based approach with just the title

---

## 2. Big Enrichment Function (ALREADY USES IMAGES ✅)
**Location:** `backend/app/services/ebay_enrichment.py` - `enrich_ebay_fields()`

### What It Does
Enriches eBay item specifics (Size, Color, Brand, Material, etc.)

### How It Works
```python
# 1. Load product JSON & get eBay schema
product_json = read_sku_json(sku)
schema_data = get_schema_for_sku(sku, use_cache=True)

# 2. COLLECT MAIN IMAGES
image_paths = _collect_main_image_paths(sku, product_json)

# 3. Build enrichment prompt with category context
system_prompt = _build_enrichment_prompt(
    category_name, category_id, 
    required_aspects, optional_aspects,
    current_fields, product_json
)

# 4. Use Vision API with images
proposed = _call_openai_vision(
    image_paths,  # IMAGES ARE USED HERE!
    system_prompt,
    all_field_names
)

# 5. Merge results
merged = _merge_fill_only(current_fields, proposed)

# 6. Save to JSON
# (required/optional split)
```

### Image Usage
- Sends 1-N main product images to OpenAI Vision
- Vision API analyzes images to extract field values
- Combined with category schema for accurate results
- Much more accurate than text-only approach

---

## 3. Usage via Frontend Bulk Button

### From UI (New 📝 SEO Button)
1. Select SKUs using checkboxes
2. Click **📝 SEO** button
3. For each selected SKU:
   ```
   POST /api/ebay/enrich-seo
   {
     "sku": "HAN000350",
     "force": false
   }
   ```
4. Backend runs updated `enrich_ebay_seo_fields()` with images
5. Results saved and shown

### Response
```json
{
  "success": true,
  "sku": "HAN000350",
  "seo_fields": {
    "product_type": "Short",
    "product_model": "Classic Summer 2024",
    "keyword_1": "summer shorts",
    "keyword_2": "comfortable shorts",
    "keyword_3": "casual wear"
  },
  "updated_seo_fields": 4,
  "message": "SEO enrichment completed"
}
```

---

## 4. Key Improvements

| Function | Before | After |
|----------|--------|-------|
| **SEO Enrichment** | Title only | Title + Main Images |
| **Fallback** | N/A | Falls back to text if no images |
| **Quality** | Text-based | Vision-based (higher accuracy) |
| **Big Enrichment** | Already uses images ✅ | Still uses images ✅ |

---

## 5. Testing Flow

### Test Case: Generate SEO for HAN000350
1. Open eBay Listings page
2. Filter for HAN000350 (Count Main Images > 1)
3. Check the checkbox
4. Click 📝 SEO button
5. Backend:
   - Loads product JSON
   - Extracts title
   - **Collects main images** ← NEW
   - **Sends images + title to OpenAI Vision** ← NEW
   - Receives product_type, keywords, model
   - Saves to JSON
6. See updated SEO fields in table

### Expected Benefits
- Better keyword suggestions (vision sees product color, style, fit)
- Accurate product type identification (from visual inspection)
- More contextual product model detection (from images)

---

## 6. Configuration

Both functions use the same OpenAI config:
- **Model:** `gpt-4-vision` (or configured via `EBAY_ENRICHMENT_MODEL`)
- **Temperature:** 0.5 (deterministic, consistent)
- **Max Tokens:** 2000

Vision-specific:
- Supports up to N images per request
- Converts images to data URIs (base64)
- Handles missing images gracefully (empty list)

---

## Summary

✅ **SEO Enrichment**: NOW uses main images for better Product Type, Keywords, and Model generation
✅ **Big Enrichment**: ALREADY uses main images for eBay item specifics
✅ **Fallback**: If no images, falls back to text-based approach
✅ **Bulk UI**: 📝 SEO button triggers vision-based enrichment for selected SKUs
✅ **Quality**: Images significantly improve AI classification accuracy
