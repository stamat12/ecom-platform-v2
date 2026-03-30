# ecom-platform-v2

FastAPI + React platform for SKU operations, image workflows, product details enrichment, eBay SEO and listing workflows, category AI, and inventory synchronization.

## Project Structure

```text
ecom-platform-v2/
	backend/
		app/
			main.py                         # API routes
			models/                         # Pydantic request/response models
			services/                       # Business logic (images, AI, eBay, inventory, sync)
			repositories/                   # JSON/cache/data access helpers
			config/                         # Runtime and feature configuration
		scripts/                          # Utility and backfill scripts
		logs/                             # Runtime logs (including category AI logs)
		.venv/                            # Python virtual environment
	frontend/
		src/
			pages/SkuBatchPage.jsx          # Main batch UI for image/details/eBay workflows
			...                             # Other pages/components
	docs/                               # Internal notes/history (cleaned as requested)
	STARTUP_GUIDE.md                    # Startup instructions
	README.md                           # This file
```

## How Every Feature Works

### 1) SKU List and Batch Navigation
- Backend provides SKU list endpoints with filtering and metadata.
- Frontend displays SKUs and allows selecting subsets for one-page bulk operations.
- Selected SKUs are passed into the batch page and reused across multiple ribbons/actions.

### 2) Image Loading and Preview
- Images per SKU are loaded from configured image base directories.
- API serves thumbnail/preview/original URLs.
- Batch UI supports preview modal, image navigation, and quick open of originals.

### 3) Image Rotation
- Frontend triggers rotate endpoint with degrees.
- Backend rotates file and invalidates cache.
- Frontend refreshes SKU images with cache-busting timestamp query values.

### 4) Image Classification
- Supports individual and batch classification calls.
- Classified labels are saved and rendered as badges.
- Classification can be used to separate phone/stock/enhanced image groups.

### 5) Main Image and eBay Image Order Handling
- Main image mark/unmark endpoints update image metadata.
- eBay order metadata is loaded and used by listing and SEO bulk views.
- UI prioritizes image with eBay order 1 when choosing representative thumbnail.

### 6) JSON Generation and JSON Status
- Per-SKU JSON existence is exposed by status endpoint.
- Generate endpoint creates/updates product JSON from SKU context and images.
- UI shows missing/existing state and can generate from detail/batch views.

### 7) Product Details Editing
- Product details are grouped by categories and fields.
- Frontend can edit per-SKU or in bulk table mode.
- Save posts category/field updates to details endpoint and refreshes local view.

### 8) AI Enrichment (Product Details)
- Single and batch enrichment endpoints fill detail fields.
- Frontend enrich actions re-fetch details after completion.
- Existing values are preserved depending on enrichment strategy in backend service.

### 9) eBay Category AI Detection
- Uses product context (title/keywords/details/brand/etc.) and optional images.
- Category tree is traversed level-by-level with AI choice among sibling options.
- Supports safe stop at parent when deeper options do not fit.
- Results are written back to product JSON and logged.
- Batch detect supports streamed progress events for live UI progress bars.

### 10) eBay SEO Fields
- SEO data model: `product_type`, `product_model`, `keyword_1`, `keyword_2`, `keyword_3`.
- Per-SKU editor inside eBay section supports save/cancel.
- Bulk SEO modal supports editing all selected SKUs in one table.
- Bulk SEO table shows representative image + Brand/Color/Size + SEO columns.

### 11) eBay Schema, Validation, and Enrichment
- Category schema can be loaded by category ID or SKU.
- Required/optional eBay fields are displayed and editable.
- Validation endpoints report completeness of required fields.
- AI enrichment can populate eBay field values for listing readiness.

### 12) eBay Listing Drafts and Creation
- Draft data includes quantity, condition, condition note, EAN, modified SKU, price, schedule.
- Profit preview is calculated in UI from total cost, fees, commission, shipping.
- Single and batch listing creation endpoints create listings through eBay API flow.
- Upload progress/status is surfaced in UI.

### 13) eBay Listing Sync and Cache
- Backend sync service fetches active listings and caches results.
- SKU listing count/status is exposed for batch UI indicators.
- Cache refresh endpoints support fast sync and recomputation workflows.

### 14) Inventory and Finance Synchronization
- Excel -> DB and JSON -> DB import/sync services normalize financial fields.
- `Total Cost Net` automation computes from `Price Net + Shipping Net` where applicable.
- Backfill scripts exist for normalizing historical values and fixing empty/missing totals.
- DB -> Excel sync writes normalized values back to source sheets.

### 15) Streaming Progress Features
- SSE-style streaming endpoints are used where long operations need live progress.
- Category detect batch stream sends `start`, `progress`, `complete`, and `error` events.
- Frontend updates progress bars using streamed payloads instead of static polling.

### 16) Logging and Debugging
- Structured category AI logs written to backend logs file for per-level decisions.
- API docs are available through FastAPI Swagger for endpoint testing.
- Additional debug endpoints/scripts exist for table inspection and cleanup tasks.

## Main Backend Route Groups

- SKU/images/details: `backend/app/main.py`
- AI enrich and category detect: `backend/app/main.py`, `backend/app/services/ebay_category_ai.py`
- eBay schema/enrich/listing/sync: `backend/app/services/ebay_*.py`
- Inventory sync/import/backfill: `backend/app/services/*sync*.py`, `backend/scripts/*.py`

## Data and Storage Notes

- Product JSON files are the source for many editable/enriched fields.
- SQLite inventory tables are used for finance/inventory normalization workflows.
- Image metadata (main/eBay order/classification) is reused across listing and SEO tools.

## Known Operational Patterns

- Use text-only category detect when image context causes wrong root branch.
- Run backfill scripts after major finance logic changes to align historical rows.
- Use bulk modals for high-throughput edits, then validate with per-SKU sections as needed.