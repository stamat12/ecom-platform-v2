## Step-by-step plan (minimal disruption)

### Phase A — Build “better GUI now” (1–2 weeks)

1. Create new repo structure:
   * `/frontend` (Next.js)
   * `/backend` (FastAPI)
   * keep your existing `agents/`, `products/`, and image folders as-is
2. Backend endpoints (file-backed)

* `GET /skus` (list from inventory Excel or from JSON directory)
* `GET /skus/{sku}` (read JSON)
* `PATCH /skus/{sku}` (update JSON fields)
* `GET /skus/{sku}/images` (from JSON Images section + folder scan)
* `POST /skus/{sku}/images/classify` (calls your classification helper, writes JSON) image_classification
* `POST /skus/{sku}/main-images` (calls selection logic, writes JSON) image_selector
* `GET /images/{sku}/{filename}` (serves file as a normal HTTP response)

3. React UI screens (fast wins)

* SKU list (filters: status, missing fields, has_main_images)
* SKU detail:
  * thumbnail grid (URLs from backend)
  * select main images + reorder
  * classify phone/stock/enhanced
  * edit fields panel

This will already feel dramatically faster than NiceGUI.

---

### Phase B — “Hybrid migration” (no downtime)

Once UI is stable:

1. Introduce SQL Server tables for:

* SKU core fields
* image metadata
* roles/orders

2. Write a one-time importer:

* reads existing JSONs → populates SQL

3. Switch reads first:

* `GET /skus`, `GET /skus/{sku}`, `GET /skus/{sku}/images` now come from SQL
* Writes can still update JSON in parallel temporarily (“write-through”) until stable

4. Move images to Blob later:

* Keep local serving in dev
* In prod, store object keys and return signed URLs

This is a safe migration path.

---

## Important constraints / pitfalls (so you don’t rebuild twice)

### Avoid these now

* Don’t let the React UI read files directly
* Don’t embed images as base64 blobs
* Don’t build endpoints that return “whatever the JSON currently looks like” without a stable schema

### Do this instead

* Define API response models (Pydantic) and keep them stable
* Treat JSON as a storage implementation, not your public API format
* Keep “agents” behind job endpoints even if initially synchronous
