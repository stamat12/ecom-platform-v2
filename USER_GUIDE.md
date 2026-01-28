# JSON Generation Feature - User Guide

## Overview
This guide explains how to use the JSON generation and status checking features across the SKU management platform.

---

## 1. SKU List View (`/skus`)

### Viewing JSON Status
- **Column 2 (JSON Status):** Shows a green checkmark (✓) or gray X (✗)
- **Green Checkmark (✓):** JSON file exists for this SKU
- **Gray X (✗):** JSON file does not exist (needs generation)

### What You See
```
Checkbox | JSON Status | SKU (Old) | Brand | Category | Color | Size | ...
✓        | ✓           | SKU123   | Nike  | Shoes    | Black | 10   | ...
✓        | ✗           | SKU124   | Adidas| Shoes    | White | 11   | ...
```

### Key Points
- Status checks happen automatically when the page loads
- Status updates when you change pages or filters
- Each SKU's status is cached to avoid duplicate requests
- Status appears before other columns for quick scanning

---

## 2. Single SKU Detail View (`/skus/{sku}`)

### Viewing JSON Status
Located in the top header next to the SKU name:
- **Green Badge:** "✓ JSON: Exists"
- **Orange Badge:** "✗ JSON: Missing" with a "Generate" button

### Example Layout
```
← Back | SKU: ABC123 | ✓ JSON: Exists | [Batch Nav buttons]
```

Or when missing:
```
← Back | SKU: ABC124 | ✗ JSON: Missing [Generate] | [Batch Nav buttons]
```

### Generating JSON

1. **If JSON is Missing:**
   - Orange badge appears automatically
   - Click the **"Generate"** button next to the badge
   - Button shows "Generating..." while processing
   - This may take 10-30 seconds depending on image size

2. **After Generation:**
   - Badge turns green showing "✓ JSON: Exists"
   - Success message appears: "JSON generated successfully!"
   - The JSON file is created/updated in the products folder

3. **If JSON Already Exists:**
   - Green badge shows "✓ JSON: Exists"
   - No generate button visible
   - JSON already generated, no action needed

### Important Notes
- Generation happens on a per-SKU basis
- Only click if you want to generate/regenerate JSON
- Each SKU can be generated independently
- Generation updates the product details JSON file with info from images

---

## 3. Batch View (`/skus/batch`)

### Viewing Multiple SKUs
Shows all selected SKUs on one page in separate sections

### JSON Status per SKU
Each SKU section has its own JSON badge:
```
SKU: ABC123 | ✓ JSON: Exists | [Open single view]
[Images grid]

SKU: ABC124 | ✗ JSON: Missing [Gen] | [Open single view]
[Images grid]

SKU: ABC125 | ✓ JSON: Exists | [Open single view]
[Images grid]
```

### Generating JSON in Batch

1. **Individual Generation:**
   - Click the **"Gen"** button next to any SKU missing JSON
   - Only that SKU generates
   - Other SKUs are unaffected
   - Multiple SKUs can generate simultaneously

2. **After Generation:**
   - That SKU's badge turns green
   - Other SKU statuses unchanged
   - You can continue managing other images

### Advantages of Batch View
- See all selected SKUs on one page
- Rotate images for multiple SKUs easily
- Generate JSON for multiple SKUs simultaneously
- Efficient workflow for bulk operations
- Compare SKUs side by side

---

## Workflow Examples

### Example 1: Single SKU Generation
```
1. Navigate to /skus
2. Click on a SKU name to open detail view
3. See orange badge "✗ JSON: Missing [Generate]"
4. Click [Generate] button
5. Wait for "JSON generated successfully!" message
6. Badge turns green ✓ JSON: Exists
```

### Example 2: Batch Generation
```
1. Navigate to /skus
2. Select multiple SKUs with checkboxes (e.g., 5 SKUs)
3. Click "View selected (one page)" button
4. Each SKU shows individual JSON status badge
5. For SKUs missing JSON, click their [Gen] buttons
6. All can generate simultaneously
7. Watch badges turn green as they complete
8. All SKUs now have JSON generated
```

### Example 3: Check Status While Filtering
```
1. Navigate to /skus
2. Apply filter (e.g., Brand = "Nike")
3. JSON status column shows ✓ or ✗ for filtered results
4. Identify which Nike SKUs need JSON generation
5. Select those SKUs
6. Generate JSON for selected items
```

---

## Technical Details (For Reference)

### What is JSON Generation?
- Creates a `{SKU}.json` file in the products folder
- Uses OpenAI vision API to analyze product images
- Fills missing product details:
  - Gender
  - Brand
  - Color
  - Size
  - Materials
  - Keywords
  - More Details

### Where Are JSON Files Stored?
- Location: `{PRODUCTS_FOLDER_PATH}/{SKU}.json`
- Created when you click Generate
- Updated if you generate again

### What Happens During Generation?
1. System reads SKU images
2. Sends images to OpenAI vision API
3. AI analyzes images and extracts product details
4. Details are merged into JSON file
5. File is saved to disk
6. Status updates to show JSON exists

### Status Check Timing
- **List Page:** Checks when page loads or filters change
- **Detail Page:** Checks when you navigate to a SKU
- **Batch Page:** Checks for each SKU when page loads

---

## Troubleshooting

### Generation Takes Too Long
- This is normal for large images
- Process extracts details from images via AI
- Typical time: 10-30 seconds
- Longer times indicate more detailed analysis

### Generation Shows Error
- Check that images are present in the SKU folder
- Verify image files are in supported formats (jpg, jpeg, png, webp)
- Ensure API keys are configured
- Contact admin if error persists

### Badge Shows Wrong Status
- Try refreshing the page
- Navigate away and back to the SKU
- Status cache may be slightly out of sync

### Can't Click Generate Button
- Button is disabled if generation is already in progress
- Wait for current generation to complete
- Check if JSON already exists (green badge shown)

---

## Tips & Best Practices

### 1. Batch Operations
- Select 5-10 SKUs at a time for batch view
- Easier to manage and compare
- Generate JSON for all at once if missing

### 2. Filtering Before Generation
- Filter by brand or category first
- Reduces number of SKUs to generate
- More efficient workflow

### 3. Image Quality
- Ensure images are clear and in supported formats
- Better images = better JSON generation results
- Main image is used for analysis

### 4. Checking Status
- Use the list view to quickly scan all SKUs
- Green checkmark = ready to export
- Gray X = needs generation before export

### 5. Batch Workflows
```
Select SKUs → Filter by missing JSON → Batch view → Generate all → Export
```

---

## Keyboard Shortcuts
- No keyboard shortcuts currently, but:
  - Click column header to sort (if available)
  - Use filter inputs to narrow results quickly
  - Checkboxes for multi-select

---

## FAQ

**Q: Can I generate JSON without images?**  
A: No, the system requires at least one image per SKU to extract details.

**Q: What if I generate JSON twice?**  
A: The second generation updates/overwrites the first one. No harm done.

**Q: How long does generation take?**  
A: Typically 10-30 seconds per SKU depending on image complexity.

**Q: Can multiple SKUs generate at the same time?**  
A: Yes, in batch view you can click multiple [Gen] buttons and they all run simultaneously.

**Q: Does generation affect my images?**  
A: No, it only creates/updates the JSON file with extracted details.

**Q: Where can I see the generated JSON?**  
A: In the products folder: `{PRODUCTS_FOLDER_PATH}/{SKU}.json`

**Q: Can I revert a generation?**  
A: Delete the JSON file manually to revert, then generate again.

---

## Support
If you encounter issues:
1. Check the troubleshooting section above
2. Verify all images are present and in correct folder
3. Try refreshing the page
4. Contact admin with error message if problem persists

---

**Version:** 1.0  
**Last Updated:** 2024  
**Feature Status:** ✅ Production Ready
