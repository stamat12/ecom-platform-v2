# AI Enrichment Implementation Guide

## Overview

The new ecom-platform-v2 now includes AI-powered product details enrichment using OpenAI's vision model. This implementation mirrors the legacy ecommerceAI system but is fully integrated into the new FastAPI backend with a React UI.

## Configuration Storage

**Location:** `backend/app/config/ai_config.py`

This is the **single source of truth** for all AI enrichment settings. You can easily edit:

- `OPENAI_MODEL` - Which OpenAI model to use (default: `gpt-4o-mini`)
- `GEMINI_MODEL` - For future EAN/price extraction (default: `gemini-1.5-pro`)
- `ENRICHABLE_FIELDS` - List of product attributes to enrich
- `FIELD_TARGETS` - Maps field names to their JSON locations
- `OPENAI_PROMPT` - The complete system prompt (in German)
- `GENDER_CODE_MAP` - Gender codes mapping (M, F, U, KB, KG, KU)
- `OPENAI_TEMPERATURE` - AI randomness (0.1 = consistent)
- `OPENAI_MAX_TOKENS` - Max response length

## API Endpoints

### Single SKU Enrichment
```
POST /api/ai/enrich/single/{sku}

Response: {
  "success": bool,
  "sku": string,
  "updated_fields": number,
  "message": string,
  "data": { field: value }
}
```

### Batch SKU Enrichment
```
POST /api/ai/enrich/batch

Request Body: {
  "skus": ["SKU1", "SKU2", ...]
}

Response: {
  "success": bool,
  "total": number,
  "succeeded": number,
  "failed": number,
  "results": { sku: {...} }
}
```

### Get Configuration
```
GET /api/ai/config

Response: {
  "model": string,
  "fields": [string],
  "prompt_preview": string
}
```

## Batch Page UI

### Enrichment Panel
- **Location:** Top section of batch page (after image classification)
- **Blue box** with "🤖 AI Product Details Enrichment" header
- **Select All / Deselect All buttons** to manage SKU selection
- **"✨ Enrich Selected SKUs" button** to start enrichment
- **Results display** showing succeeded/failed counts

### SKU Selection
- **Checkbox** next to each SKU name in the batch cards
- Click to select/deselect that SKU for enrichment
- Count display: "X selected"

## Process Flow

1. **Select SKUs** - Use checkboxes in enrichment panel or individual SKU cards
2. **Click Enrich Button** - Starts batch enrichment for all selected SKUs
3. **Backend Process:**
   - For each SKU:
     - Load product JSON
     - Find main images from `Images.main_images` array
     - Call OpenAI vision API with all main images
     - Extract: Gender, Brand, Color, Size, More Details, Keywords, Materials
     - Only fill empty fields (preserves existing data)
     - Normalize gender codes (M/F/U/KB/KG/KU)
     - Write back to nested JSON locations
     - Save updated product JSON
4. **Results Display** - Shows which SKUs succeeded and how many fields were filled

## Enriched Fields

All fields are **optional** and only filled if empty:

| Field | Location | Format |
|-------|----------|--------|
| Gender | Intern Product Info | Single code: M, F, U, KB, KG, KU |
| Brand | Intern Product Info | Text (free) |
| Color | Intern Product Info | Text (free) |
| Size | Intern Product Info | Text (free) |
| More Details | Intern Generated Info | 2-5 German sentences |
| Keywords | Intern Generated Info | Space-separated German words (no commas) |
| Materials | Intern Generated Info | Text (free) |

## Key Features

✅ **Vision-based extraction** - Analyzes actual product images  
✅ **German output enforced** - All text in German per business rules  
✅ **Preserves existing data** - Only fills empty fields  
✅ **Gender code normalization** - Converts free text to standard codes  
✅ **Batch processing** - Enrich multiple SKUs at once  
✅ **Easy config editing** - All settings in one Python file  
✅ **Results tracking** - See which SKUs succeeded/failed  

## To Change Model or Prompt

1. Open `backend/app/config/ai_config.py`
2. Edit `OPENAI_MODEL` or `OPENAI_PROMPT`
3. No other changes needed - changes apply instantly

Example: Switch to GPT-4 Turbo
```python
OPENAI_MODEL = "gpt-4-turbo"
```

Example: Customize the prompt
```python
OPENAI_PROMPT = "Your custom prompt here..."
```

## Environment Variables Required

In `backend/.env`:
```
OPENAI_API_KEY=sk-your-key-here
GEMINI_API_KEY=optional-key-here
EBAY_APP_ID=optional
EBAY_CERT_ID=optional
EBAY_API_TOKEN=optional
```

## Error Handling

- **No main images found** - Returns error with message
- **Image analysis fails** - Returns empty fields with error message
- **JSON parsing fails** - Logs error and skips that SKU
- **API rate limits** - Handles gracefully, logs and continues

## Future Extensions

Ready to add:
- Gemini vision for EAN/price extraction
- eBay category classification
- Multiple image analysis strategies
- Caching of results
- Admin dashboard for batch monitoring

---

**Implemented:** January 18, 2026  
**Based on:** Legacy ecommerceAI agents/product_details_basic_openai.py
