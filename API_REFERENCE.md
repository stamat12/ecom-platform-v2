# JSON Integration - API Reference

## Base URL
```
http://localhost:8000
```

## Endpoints

### 1. Get JSON Status for a SKU

**Endpoint:**
```
GET /api/skus/{sku}/json/status
```

**Parameters:**
- `sku` (path, required): The SKU identifier
- Example: `/api/skus/ABC123/json/status`

**Request Example:**
```bash
curl -X GET "http://localhost:8000/api/skus/ABC123/json/status"
```

**Response (Success - 200 OK):**
```json
{
  "sku": "ABC123",
  "json_exists": true
}
```

**Response (JSON Missing):**
```json
{
  "sku": "ABC124",
  "json_exists": false
}
```

**Response Headers:**
```
Content-Type: application/json
```

**Status Codes:**
- `200 OK` - Request successful
- `422 Unprocessable Entity` - Invalid SKU format
- `500 Internal Server Error` - Server error

---

### 2. Generate JSON for a SKU

**Endpoint:**
```
POST /api/skus/{sku}/json/generate
```

**Parameters:**
- `sku` (path, required): The SKU identifier
- Example: `/api/skus/ABC123/json/generate`

**Request Body (JSON):**
```json
{
  "sku": "ABC123"
}
```

**Request Example:**
```bash
curl -X POST "http://localhost:8000/api/skus/ABC123/json/generate" \
  -H "Content-Type: application/json" \
  -d '{"sku":"ABC123"}'
```

**Response (Success - 200 OK):**
```json
{
  "sku": "ABC123",
  "success": true,
  "message": "JSON generated successfully for SKU: ABC123"
}
```

**Response (Failure - 200 OK with success=false):**
```json
{
  "sku": "ABC123",
  "success": false,
  "message": "Failed to generate JSON: No images found for SKU"
}
```

**Response (SKU Mismatch - 400 Bad Request):**
```json
{
  "detail": "SKU mismatch"
}
```

**Response Headers:**
```
Content-Type: application/json
```

**Status Codes:**
- `200 OK` - Request processed (check success field)
- `400 Bad Request` - SKU mismatch or invalid format
- `422 Unprocessable Entity` - Invalid request body
- `500 Internal Server Error` - Server error

---

### 3. Get SKU Images with JSON Status

**Endpoint:**
```
GET /api/skus/{sku}/images
```

**Parameters:**
- `sku` (path, required): The SKU identifier

**Request Example:**
```bash
curl -X GET "http://localhost:8000/api/skus/ABC123/images"
```

**Response (Success - 200 OK):**
```json
{
  "sku": "ABC123",
  "folder_found": true,
  "count": 45,
  "json_exists": true,
  "main_images": ["main_1.jpg"],
  "ebay_images": ["ebay_1.jpg", "ebay_2.jpg"],
  "images": [
    {
      "filename": "image_001.jpg",
      "classification": "main",
      "is_main": true,
      "is_ebay": false,
      "meta": {},
      "thumb_url": "/api/images/ABC123/image_001.jpg?variant=thumb_256",
      "preview_url": "/api/images/ABC123/image_001.jpg?variant=thumb_512",
      "original_url": "/api/images/ABC123/image_001.jpg?variant=original",
      "source": "folder"
    },
    {
      "filename": "image_002.jpg",
      "classification": null,
      "is_main": false,
      "is_ebay": false,
      "meta": {},
      "thumb_url": "/api/images/ABC123/image_002.jpg?variant=thumb_256",
      "preview_url": "/api/images/ABC123/image_002.jpg?variant=thumb_512",
      "original_url": "/api/images/ABC123/image_002.jpg?variant=original",
      "source": "folder"
    }
  ]
}
```

**Note:** The `json_exists` field (boolean) indicates if JSON exists for this SKU.

---

## Data Models (Pydantic)

### JsonStatusResponse
```python
class JsonStatusResponse(BaseModel):
    sku: str                    # SKU identifier
    json_exists: bool           # True if JSON file exists
```

### JsonGenerateRequest
```python
class JsonGenerateRequest(BaseModel):
    sku: str                    # SKU identifier
```

### JsonGenerateResponse
```python
class JsonGenerateResponse(BaseModel):
    sku: str                    # SKU identifier
    success: bool               # True if generation succeeded
    message: str                # Human-readable status message
```

### ImageInfo (from SkuImagesResponse)
```python
class ImageInfo(BaseModel):
    filename: str               # Image file name
    classification: str | None  # Image type/classification
    is_main: bool               # True if main product image
    is_ebay: bool               # True if eBay image
    meta: Dict[str, Any]        # Additional metadata
    thumb_url: str              # URL to thumbnail (256px)
    preview_url: str            # URL to preview (512px)
    original_url: str           # URL to original image
    source: str | None          # Image source
```

### SkuImagesResponse
```python
class SkuImagesResponse(BaseModel):
    sku: str                    # SKU identifier
    folder_found: bool          # True if image folder exists
    count: int                  # Total number of images
    json_exists: bool           # True if JSON file exists ← NEW!
    main_images: List[str]      # List of main image filenames
    ebay_images: List[str]      # List of eBay image filenames
    images: List[ImageInfo]     # Complete image list with URLs
```

---

## Error Handling

### Common Error Responses

**Invalid SKU Format (422):**
```json
{
  "detail": [
    {
      "loc": ["path", "sku"],
      "msg": "string",
      "type": "type_error.string"
    }
  ]
}
```

**SKU Mismatch (400):**
```json
{
  "detail": "SKU mismatch"
}
```

**Generation Failure (200 with success=false):**
```json
{
  "sku": "ABC123",
  "success": false,
  "message": "Failed to generate JSON: [specific error message]"
}
```

**Server Error (500):**
```json
{
  "detail": "Internal server error"
}
```

---

## HTTP Headers

### Request Headers
```
Content-Type: application/json
User-Agent: (your client)
Accept: application/json
```

### Response Headers
```
Content-Type: application/json; charset=utf-8
Access-Control-Allow-Origin: http://localhost:3000
Access-Control-Allow-Methods: *
Access-Control-Allow-Headers: *
```

---

## CORS Configuration

The API is configured with CORS middleware to allow:
- **Origin:** `http://localhost:3000`
- **Methods:** All HTTP methods
- **Headers:** All headers

---

## Rate Limiting

Currently no rate limiting is implemented.

---

## Authentication

Currently no authentication is required.

---

## Example Workflows

### Workflow 1: Check if JSON Exists
```bash
# Get SKU details with JSON status
curl -X GET "http://localhost:8000/api/skus/ABC123/images"

# Response includes "json_exists": true/false
# Also check with dedicated endpoint:
curl -X GET "http://localhost:8000/api/skus/ABC123/json/status"
```

### Workflow 2: Generate JSON
```bash
# POST request to generate JSON
curl -X POST "http://localhost:8000/api/skus/ABC123/json/generate" \
  -H "Content-Type: application/json" \
  -d '{"sku":"ABC123"}'

# Response includes success status and message
# Follow up with GET to verify:
curl -X GET "http://localhost:8000/api/skus/ABC123/json/status"
```

### Workflow 3: Batch Status Check
```bash
# For each SKU in list:
for sku in ABC123 ABC124 ABC125; do
  curl -X GET "http://localhost:8000/api/skus/$sku/json/status" \
    -w "\n"
done
```

---

## Response Time Expectations

| Operation | Time |
|-----------|------|
| Check JSON status | < 100ms |
| Get images (with status) | 100-500ms |
| Generate JSON | 10-30 seconds |
| Error responses | < 100ms |

---

## Testing with curl

### Quick Test: Check Status
```bash
curl -X GET "http://localhost:8000/api/skus/TEST/json/status" | jq
```

### Quick Test: Generate JSON
```bash
curl -X POST "http://localhost:8000/api/skus/TEST/json/generate" \
  -H "Content-Type: application/json" \
  -d '{"sku":"TEST"}' | jq
```

### Quick Test: Get Images with Status
```bash
curl -X GET "http://localhost:8000/api/skus/TEST/images" | jq '.json_exists'
```

---

## Integration Notes

### For Frontend Developers
1. Always include `Content-Type: application/json` header
2. Check `success` field in generate response
3. Handle network timeouts (generation may take 30+ seconds)
4. Show loading state during generation
5. Update UI after successful generation

### For Backend Developers
1. Service functions handle all errors gracefully
2. Pydantic models enforce type safety
3. API always returns 200 (check success field for actual status)
4. Images endpoint includes json_exists for convenience
5. No database used - file system based

### For DevOps/System Admins
1. Ensure `PRODUCTS_FOLDER_PATH` is configured
2. Ensure `IMAGE_FOLDER_PATHS` is configured for images
3. Ensure sufficient disk space for JSON files
4. Monitor generation times (may indicate API issues)
5. Configure OpenAI API key for generation to work

---

## Migration Notes

### Breaking Changes
None - all additions are backward compatible.

### New Fields
- `json_exists` in `SkuImagesResponse`
- `json_exists` returned by `/api/skus/{sku}/images`

### Deprecated Endpoints
None

### Future Changes
- Possible WebSocket for real-time generation progress
- Batch generation endpoint
- Generation history tracking
- Product detail field validation

---

## Product Details Endpoints

### 13. Get Product Details for a SKU

**Endpoint:**
```
GET /api/skus/{sku}/details
```

**Description:**
Returns complete product details with all categories and fields. Provides completion statistics and highlights important fields (gender, brand, color, size, etc.).

**Parameters:**
- `sku` (path, required): The SKU identifier

**Response (200 OK):**
```json
{
  "sku": "JAL00001",
  "exists": true,
  "categories": [
    {
      "name": "Invoice Data",
      "fields": [
        {
          "name": "Buying Entity",
          "value": "Stamen Gochev",
          "is_highlighted": false
        },
        {
          "name": "Supplier",
          "value": "JLI Trading Limited",
          "is_highlighted": false
        }
      ]
    },
    {
      "name": "Intern Product Info",
      "fields": [
        {
          "name": "Gender",
          "value": "KU",
          "is_highlighted": true
        },
        {
          "name": "Brand",
          "value": "Kyopp",
          "is_highlighted": true
        }
      ]
    }
  ],
  "total_categories": 12,
  "total_fields": 45,
  "filled_fields": 38,
  "completion_percentage": 84.4
}
```

**Status Codes:**
- `200 OK` - Successfully retrieved product details
- `422 Unprocessable Entity` - Invalid SKU format

---

### 14. Update Product Details for a SKU

**Endpoint:**
```
POST /api/skus/{sku}/details
```

**Description:**
Update product detail fields. Accepts updates in nested format by category. Images category is protected and cannot be updated through this endpoint.

**Parameters:**
- `sku` (path, required): The SKU identifier

**Request Body:**
```json
{
  "sku": "JAL00001",
  "updates": {
    "Intern Product Info": {
      "Gender": "M",
      "Brand": "NewBrand",
      "Color": "Red"
    },
    "Price Data": {
      "Price Net": "15.50"
    }
  }
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Successfully updated 4 field(s)",
  "updated_fields": 4
}
```

**Response (Error - 500):**
```json
{
  "detail": "Failed to save: Permission denied"
}
```

**Status Codes:**
- `200 OK` - Successfully updated
- `400 Bad Request` - SKU mismatch between path and body
- `500 Internal Server Error` - Failed to save
- `422 Unprocessable Entity` - Invalid request format

---

**API Version:** 1.0  
**Last Updated:** 2024  
**Status:** Stable  
**Production Ready:** Yes

```
- Batch generation endpoint
- Generation history tracking

---

**API Version:** 1.0  
**Last Updated:** 2024  
**Status:** Stable  
**Production Ready:** Yes
