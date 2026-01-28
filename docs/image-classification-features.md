# Image Classification Features

## Overview
The platform now supports comprehensive image classification with visual labels, select-all functionality, and cross-SKU batch processing.

## Features Implemented

### 1. Visual Classification Labels
- **Location**: Top-right corner of each image card
- **Types**:
  - 📱 Phone (Blue badge #2196F3)
  - 📦 Stock (Orange badge #FF9800)
  - ✨ Enhanced (Purple badge #9C27B0)
  - Unclassified: No badge shown
- **Pages**: Both SKU Detail Page and SKU Batch Page

### 2. Select All Functionality
- **SKU Detail Page**: "Select All" and "Deselect All" buttons in right sidebar
- **SKU Batch Page**: "Select All" button in each SKU header
- **Behavior**: Selects all images for that specific SKU

### 3. Cross-SKU Batch Classification
- **Global Selection Panel**: Appears at top when any images are selected across SKUs
- **Display**: Shows total images selected and SKU count
- **Actions**:
  - Classify All as Phone (blue button)
  - Classify All as Stock (orange button)
  - Classify All as Enhanced (purple button)
  - Clear All Selections (gray button)
- **Workflow**: Select images from multiple SKUs → classify all at once

## Backend Architecture

### New Endpoint
```
POST /api/images/classify-batch
```

**Request**:
```json
{
  "images": [
    {"sku": "VER02000", "filename": "image1.jpg"},
    {"sku": "VER02001", "filename": "image2.jpg"}
  ],
  "classification_type": "phone"
}
```

**Response**:
```json
{
  "success": true,
  "message": "Processed 2 images across 2 SKUs",
  "processed_count": 2,
  "classification_type": "phone",
  "results": [
    {"sku": "VER02000", "filename": "image1.jpg", "success": true, "error": null},
    {"sku": "VER02001", "filename": "image2.jpg", "success": true, "error": null}
  ]
}
```

### Service Layer
- **File**: `backend/app/services/image_classification.py`
- **Function**: `classify_images(sku, filenames, classification_type)`
- **Behavior**: 
  - Reads JSON file for SKU
  - Removes filenames from all classification categories
  - Adds to target category
  - Updates Images section with summary

### Pydantic Models
- **File**: `backend/app/models/batch_image_classification.py`
- **Models**:
  - `ImageReference` - SKU + filename pair
  - `BatchImageClassificationRequest` - Array of image references + type
  - `BatchImageClassificationResponse` - Results with per-image status

## Frontend State Management

### SKU Detail Page
```javascript
selectedImages: []  // Array of filenames
classifying: boolean
```

### SKU Batch Page
```javascript
selectedImages: {sku: [filenames]}  // Per-SKU selection
classifying: {sku: boolean}  // Per-SKU loading state
batchClassifying: boolean  // Global batch operation state
```

## User Workflow Examples

### Example 1: Single SKU Classification
1. Open SKU detail page
2. Click "Select All" in sidebar
3. Click classification button (Phone/Stock/Enhanced)
4. Images updated with classification badges

### Example 2: Cross-SKU Batch Classification
1. Open SKU batch page with multiple SKUs
2. Select specific images from different SKUs
3. Global panel appears showing selection count
4. Click "Classify All as Phone" (or Stock/Enhanced)
5. All selected images across all SKUs classified at once
6. Badges appear on all classified images

### Example 3: Mixed Selection
1. SKU A: Select 3 images
2. SKU B: Select 5 images
3. SKU C: Select 2 images
4. Global panel shows "10 image(s) selected across 3 SKU(s)"
5. Classify all 10 images as "stock" in one action

## Data Storage

### JSON Structure
```json
{
  "SKU": {
    "Images": {
      "schema_version": "1.0",
      "summary": {
        "has_phone": true,
        "has_stock": false,
        "has_enhanced": false,
        "count_phone": 3,
        "count_stock": 0,
        "count_enhanced": 0
      },
      "phone": [
        {"filename": "image1.jpg"},
        {"filename": "image2.jpg"},
        {"filename": "image3.jpg"}
      ],
      "stock": [],
      "enhanced": []
    }
  }
}
```

### API Response (Image Info)
```json
{
  "filename": "image1.jpg",
  "classification": "phone",
  "is_main": false,
  "is_ebay": false,
  "thumb_url": "/api/images/VER02000/image1.jpg?variant=thumb_256",
  "preview_url": "/api/images/VER02000/image1.jpg?variant=thumb_512",
  "original_url": "/api/images/VER02000/image1.jpg?variant=original",
  "source": "unzipped"
}
```

## Architectural Compliance

✅ **Stable Pydantic Schemas**: All endpoints return stable models  
✅ **No Direct File Reading**: Frontend calls APIs, backend handles JSON  
✅ **No Base64 Embedding**: Images served via proxy URLs  
✅ **Agents Behind Service Layer**: Classification logic wrapped in service  
✅ **JSON as Storage**: Classification stored in JSON, exposed via stable API  

## Testing Checklist

- [ ] Visual badges appear on classified images
- [ ] "Select All" works on detail page
- [ ] "Select All" works on batch page (per SKU)
- [ ] Cross-SKU selection shows global panel
- [ ] Batch classify endpoint processes multiple SKUs
- [ ] Classifications saved to JSON correctly
- [ ] Images refresh after classification
- [ ] Badges persist after page reload
- [ ] "Clear All Selections" clears global selection state

## Known Limitations

None - all requested features implemented.

## Future Enhancements

Potential additions:
- Drag-and-drop to classify
- Undo classification
- Bulk unclassify
- Classification history/audit log
- Keyboard shortcuts for classification
