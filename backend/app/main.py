from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from app.services.legacy_imports import add_legacy_to_syspath
import json

# Ensure legacy imports work
add_legacy_to_syspath()

# Import services
from app.services.sku_list import list_skus, get_available_columns, get_default_columns, get_columns_meta, get_distinct_values
from app.services.image_listing import list_images_for_sku
from app.services.image_serving import resolve_image_path
from app.services.image_rotation import rotate_image, clear_image_cache
from app.services.json_generation import check_json_exists, generate_json_for_sku
from app.services.image_classification import classify_images
from app.services.main_image import mark_main_images, unmark_main_images
from app.services.product_detail import get_product_detail, update_product_detail
from app.services.ai_enrichment import enrich_sku_fields, enrich_multiple_skus
from app.repositories.sku_json_repo import read_sku_json
from app.repositories.preferences_repo import get_sku_filter_state, save_sku_filter_state
from app.services.folder_images_cache import get_last_update_time as get_folder_images_last_update
from app.services.folder_images_computation import compute_folder_images_for_all_skus
from app.services.ebay_listings_cache import get_last_update_time as get_ebay_listings_last_update, read_cache as read_ebay_cache
from app.services.ebay_listings_computation import compute_ebay_listings

# Import eBay services
from app.services import ebay_schema, ebay_enrichment, ebay_listing, ebay_sync

# Import models
from app.models.sku_list import (
    SkuImagesResponse,
    ImageInfo,
    SkuColumnsResponse,
    SkuListResponse,
    SkuFilterState,
    SkuFilterStateResponse,
    SkuColumnMetaResponse,
    ColumnMeta,
    DistinctValuesResponse,
)
from app.models.image_operations import (
    ImageRotateRequest, ImageRotateResponse, 
    JsonStatusResponse, JsonGenerateResponse, 
    SkuDetailResponse
)
from app.models.image_classification import ImageClassificationRequest, ImageClassificationResponse
from app.models.batch_image_classification import BatchImageClassificationRequest, BatchImageClassificationResponse
from app.models.main_image import MainImageRequest, MainImageResponse, BatchMainImageRequest, BatchMainImageResponse
from app.models.product_detail import ProductDetailResponse, UpdateProductDetailRequest, UpdateProductDetailResponse
from app.models.ai_enrichment import EnrichSingleRequest, EnrichSingleResponse, EnrichBatchRequest, EnrichBatchResponse, AIConfigResponse
from app.config import ai_config

# Import eBay models
from app.models.ebay_schema import EbaySchemaResponse, EbaySchemaListResponse, EbaySchemaRefreshRequest, EbaySchemaRefreshResponse
from app.models.ebay_enrichment import EbayEnrichRequest, EbayEnrichResponse, EbayBatchEnrichRequest, EbayBatchEnrichResponse, EbayValidationRequest, EbayValidationResponse
from app.models.ebay_listing import (
    ImageUploadRequest, ImageUploadResponse,
    ManufacturerLookupRequest, ManufacturerLookupResponse,
    CreateListingRequest, CreateListingResponse,
    ListingPreviewRequest, ListingPreviewResponse,
    BatchCreateListingRequest, BatchCreateListingResponse
)
from app.models.ebay_sync import (
    SyncListingsRequest, SyncListingsResponse,
    ListingCountsResponse,
    SyncStatusRequest, SyncStatusResponse
)

# Create FastAPI app
app = FastAPI(title="Ecom Platform API", version="1.0")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "ok"}


@app.get("/api/skus/columns", response_model=SkuColumnsResponse)
def get_sku_columns():
    """Get all available columns and default columns for filtering and selection"""
    columns = get_available_columns()
    defaults = get_default_columns()
    return SkuColumnsResponse(
        columns=columns,
        total_columns=len(columns),
        default_columns=defaults
    )


@app.get("/api/skus/columns/meta", response_model=SkuColumnMetaResponse)
def get_sku_columns_meta():
    """Get column metadata including inferred types and allowed operators."""
    meta = get_columns_meta()
    return SkuColumnMetaResponse(
        columns=[ColumnMeta(**m) for m in meta],
        total_columns=len(meta),
    )


@app.get("/api/skus/filters", response_model=SkuFilterStateResponse)
def get_sku_filters(profile_id: str = Query("default", description="Profile identifier")):
    """Get persisted filter state for the SKU list page."""
    state = get_sku_filter_state(profile_id)
    return SkuFilterStateResponse(
        profile_id=state["profile_id"],
        selected_columns=state.get("selected_columns", []),
        column_filters=state.get("column_filters", {}),
        page_size=state.get("page_size", 50),
        column_widths=state.get("column_widths", {}),
    )


@app.put("/api/skus/filters", response_model=SkuFilterStateResponse)
def put_sku_filters(request: SkuFilterState):
    """Persist filter state for the SKU list page (stable schema)."""
    saved = save_sku_filter_state(request.model_dump())
    return SkuFilterStateResponse(
        profile_id=saved["profile_id"],
        selected_columns=saved.get("selected_columns", []),
        column_filters=saved.get("column_filters", {}),
        page_size=saved.get("page_size", 50),
        column_widths=saved.get("column_widths", {}),
    )


@app.get("/api/skus", response_model=SkuListResponse)
def get_skus(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    columns: str | None = Query(None, description="Comma-separated column names to include"),
    filters: str | None = Query(None, description="JSON string of column filters"),
):
    """
    List SKUs with per-column filtering support.
    
    filters format: JSON list of {column, value, operator} objects
    Example: [{"column": "Brand", "value": "Nike", "operator": "equals"}]
    """
    # Parse columns parameter if provided
    columns_list = None
    if columns:
        columns_list = [col.strip() for col in columns.split(",")]
    
    # Parse filters parameter if provided
    filters_list = None
    if filters:
        try:
            filters_list = json.loads(filters)
        except json.JSONDecodeError:
            filters_list = None
    
    data = list_skus(page=page, page_size=page_size, filters=filters_list, columns=columns_list)
    return SkuListResponse(
        page=data["page"],
        page_size=data["page_size"],
        total=data["total"],
        items=data["items"],
        available_columns=data.get("available_columns")
    )


@app.get("/api/skus/{sku}", response_model=SkuDetailResponse)
def get_sku_detail(sku: str):
    """Get detailed data for a single SKU (from JSON file)"""
    data = read_sku_json(sku)
    return SkuDetailResponse(
        sku=sku,
        data=data if data else {},
        exists=bool(data)
    )


@app.get("/api/skus/{sku}/images", response_model=SkuImagesResponse)
def get_sku_images(sku: str):
    """Get images for a specific SKU"""
    data = list_images_for_sku(sku)
    return SkuImagesResponse(
        sku=data["sku"],
        folder_found=data["folder_found"],
        count=data["count"],
        main_images=data.get("main_images", []),
        ebay_images=data.get("ebay_images", []),
        images=[ImageInfo(**img) for img in data["images"]]
    )


@app.get("/api/images/{sku}/{filename}")
def get_image(
    sku: str,
    filename: str,
    variant: str = Query("original", description="original | thumb_256 | thumb_512"),
):
    """Serve image file with optional resizing"""
    try:
        path = resolve_image_path(sku, filename, variant)
        return FileResponse(path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Image not found")


@app.post("/api/images/{sku}/{filename}/rotate", response_model=ImageRotateResponse)
def rotate_image_endpoint(
    sku: str,
    filename: str,
    request: ImageRotateRequest,
):
    """Rotate an image by 90, 180, or 270 degrees clockwise"""
    if request.sku != sku or request.filename != filename:
        raise HTTPException(status_code=400, detail="SKU/filename mismatch")
    
    result = rotate_image(sku, filename, request.degrees)
    
    if result["success"]:
        clear_image_cache(sku, filename)
    
    return ImageRotateResponse(**result)


@app.get("/api/skus/{sku}/json/status", response_model=JsonStatusResponse)
def get_json_status(sku: str):
    """Check if JSON file exists for a SKU"""
    exists = check_json_exists(sku)
    return JsonStatusResponse(sku=sku, json_exists=exists)


@app.post("/api/skus/{sku}/json/generate", response_model=JsonGenerateResponse)
def generate_json_endpoint(sku: str):
    """Generate JSON for a SKU from inventory database"""
    try:
        result = generate_json_for_sku(sku)
        return JsonGenerateResponse(**result)
    except Exception as e:
        return JsonGenerateResponse(
            sku=sku,
            success=False,
            message=f"Error generating JSON: {str(e)}"
        )


@app.post("/api/skus/{sku}/images/classify", response_model=ImageClassificationResponse)
def classify_images_endpoint(sku: str, request: ImageClassificationRequest):
    """Classify images for a SKU (phone/stock/enhanced)"""
    if request.sku != sku:
        raise HTTPException(status_code=400, detail="SKU mismatch")
    
    result = classify_images(sku, request.filenames, request.classification_type)
    return ImageClassificationResponse(**result)


@app.post("/api/images/classify-batch", response_model=BatchImageClassificationResponse)
def classify_images_batch_endpoint(request: BatchImageClassificationRequest):
    """Classify multiple images across multiple SKUs in one operation"""
    results = []
    processed_count = 0
    
    # Group images by SKU
    sku_groups = {}
    for img_ref in request.images:
        if img_ref.sku not in sku_groups:
            sku_groups[img_ref.sku] = []
        sku_groups[img_ref.sku].append(img_ref.filename)
    
    # Process each SKU
    for sku, filenames in sku_groups.items():
        try:
            result = classify_images(sku, filenames, request.classification_type)
            if result["success"]:
                processed_count += len(filenames)
                for fn in filenames:
                    results.append({
                        "sku": sku,
                        "filename": fn,
                        "success": True,
                        "error": None
                    })
            else:
                for fn in filenames:
                    results.append({
                        "sku": sku,
                        "filename": fn,
                        "success": False,
                        "error": result.get("message", "Unknown error")
                    })
        except Exception as e:
            for fn in filenames:
                results.append({
                    "sku": sku,
                    "filename": fn,
                    "success": False,
                    "error": str(e)
                })
    
    return BatchImageClassificationResponse(
        success=processed_count > 0,
        message=f"Processed {processed_count} images across {len(sku_groups)} SKUs",
        processed_count=processed_count,
        classification_type=request.classification_type,
        results=results
    )


@app.post("/api/skus/{sku}/images/mark-main", response_model=MainImageResponse)
def mark_main_images_endpoint(sku: str, request: MainImageRequest):
    """Mark images as main images for a SKU"""
    if request.sku != sku:
        raise HTTPException(status_code=400, detail="SKU mismatch")
    
    result = mark_main_images(sku, request.filenames)
    return MainImageResponse(**result)


@app.post("/api/skus/{sku}/images/unmark-main", response_model=MainImageResponse)
def unmark_main_images_endpoint(sku: str, request: MainImageRequest):
    """Unmark images as main images for a SKU"""
    if request.sku != sku:
        raise HTTPException(status_code=400, detail="SKU mismatch")
    
    result = unmark_main_images(sku, request.filenames)
    return MainImageResponse(**result)


@app.post("/api/images/main-batch", response_model=BatchMainImageResponse)
def batch_main_images_endpoint(request: BatchMainImageRequest):
    """Mark or unmark images as main across multiple SKUs"""
    results = []
    processed_count = 0
    
    # Group images by SKU
    sku_groups = {}
    for img_ref in request.images:
        sku = img_ref.get("sku")
        filename = img_ref.get("filename")
        if not sku or not filename:
            continue
        if sku not in sku_groups:
            sku_groups[sku] = []
        sku_groups[sku].append(filename)
    
    # Process each SKU
    for sku, filenames in sku_groups.items():
        try:
            if request.action == "mark":
                result = mark_main_images(sku, filenames)
            elif request.action == "unmark":
                result = unmark_main_images(sku, filenames)
            else:
                raise ValueError(f"Invalid action: {request.action}")
            
            if result["success"]:
                processed_count += result["processed_count"]
                for fn in filenames:
                    results.append({
                        "sku": sku,
                        "filename": fn,
                        "success": True,
                        "error": None
                    })
            else:
                for fn in filenames:
                    results.append({
                        "sku": sku,
                        "filename": fn,
                        "success": False,
                        "error": result.get("message", "Unknown error")
                    })
        except Exception as e:
            for fn in filenames:
                results.append({
                    "sku": sku,
                    "filename": fn,
                    "success": False,
                    "error": str(e)
                })
    
    action_word = "marked" if request.action == "mark" else "unmarked"
    return BatchMainImageResponse(
        success=processed_count > 0,
        message=f"{action_word.capitalize()} {processed_count} image(s) as main across {len(sku_groups)} SKU(s)",
        processed_count=processed_count,
        results=results
    )

# ============================================================================
# PRODUCT DETAIL ENDPOINTS
# ============================================================================

@app.get("/api/skus/{sku}/details", response_model=ProductDetailResponse)
def get_sku_product_details(sku: str):
    """
    Get complete product details for a SKU.
    Returns all categories and fields with completion statistics.
    """
    return get_product_detail(sku)


@app.post("/api/skus/{sku}/details", response_model=UpdateProductDetailResponse)
def update_sku_product_details(sku: str, request: UpdateProductDetailRequest):
    """
    Update product detail fields for a SKU.
    Accepts updates in format {'Category Name': {'Field Name': 'New Value'}}.
    """
    if request.sku != sku:
        raise HTTPException(status_code=400, detail="SKU in path must match SKU in request body")
    
    success, message, updated_count = update_product_detail(sku, request.updates)
    
    if not success:
        raise HTTPException(status_code=500, detail=message)
    
    return UpdateProductDetailResponse(
        success=True,
        message=message,
        updated_fields=updated_count
    )


# ============================================================
# AI Enrichment Endpoints
# ============================================================

@app.post("/api/ai/enrich/single/{sku}", response_model=EnrichSingleResponse)
def enrich_single_sku(sku: str):
    """
    Enrich product details for a single SKU using OpenAI vision.
    Extracts: Gender, Brand, Color, Size, More Details, Keywords, Materials.
    """
    result = enrich_sku_fields(sku)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    
    return EnrichSingleResponse(
        success=True,
        sku=sku,
        updated_fields=result.get("updated_fields"),
        message=result.get("message"),
        data=result.get("data")
    )


@app.post("/api/ai/enrich/batch", response_model=EnrichBatchResponse)
def enrich_batch_skus(request: EnrichBatchRequest):
    """
    Enrich product details for multiple SKUs in batch.
    """
    if not request.skus or len(request.skus) == 0:
        raise HTTPException(status_code=400, detail="At least one SKU required")
    
    result = enrich_multiple_skus(request.skus)
    
    return EnrichBatchResponse(
        success=result.get("success"),
        total=result.get("total"),
        succeeded=result.get("succeeded"),
        failed=result.get("failed"),
        results=result.get("results")
    )


@app.get("/api/ai/config", response_model=AIConfigResponse)
def get_ai_config():
    """
    Get current AI enrichment configuration.
    """
    prompt_preview = ai_config.OPENAI_PROMPT[:200] + "..."
    
    return AIConfigResponse(
        model=ai_config.OPENAI_MODEL,
        fields=ai_config.ENRICHABLE_FIELDS,
        prompt_preview=prompt_preview
    )


@app.get("/api/skus/columns/distinct", response_model=DistinctValuesResponse)
def get_distinct(
    column: str = Query(..., description="Column name"),
    limit: int = Query(200, ge=1, le=1000),
    q: str | None = Query(None, description="Optional substring filter (case-insensitive)"),
):
    """Get distinct values for a column for multi-select UIs."""
    meta = get_available_columns()
    if column not in meta:
        raise HTTPException(status_code=400, detail="Invalid column")
    result = get_distinct_values(column, limit=limit, q=q)
    return DistinctValuesResponse(**result)


# ============================================================
# eBay Schema Endpoints
# ============================================================

@app.get("/api/ebay/schemas/{category_id}", response_model=EbaySchemaResponse)
def get_ebay_schema(
    category_id: str,
    use_cache: bool = Query(True, description="Use cached schema if available")
):
    """Get eBay category schema by category ID"""
    try:
        schema_data = ebay_schema.get_schema(category_id, use_cache=use_cache)
        
        if not schema_data:
            return EbaySchemaResponse(
                success=False,
                category_id=category_id,
                message="Schema not found"
            )
        
        metadata = schema_data.get("_metadata", {})
        schema = schema_data.get("schema", {})
        
        return EbaySchemaResponse(
            success=True,
            category_id=category_id,
            category_name=metadata.get("category_name"),
            metadata=metadata,
            schema=schema,
            cached=use_cache,
            message="Schema retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ebay/schemas/sku/{sku}")
def get_ebay_schema_for_sku(
    sku: str,
    use_cache: bool = Query(True, description="Use cached schema if available")
):
    """Get eBay category schema for SKU's category"""
    try:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"API: Getting eBay schema for SKU: {sku}")
        
        schema_data = ebay_schema.get_schema_for_sku(sku, use_cache=use_cache)
        
        if not schema_data:
            logger.warning(f"No schema found for SKU {sku}")
            return {
                "success": False,
                "category_id": "",
                "message": f"No schema found for SKU {sku}"
            }
        
        metadata = schema_data.get("_metadata", {})
        schema = schema_data.get("schema", {})
        
        logger.info(f"Returning schema for SKU {sku}: category_id={metadata.get('category_id')}")
        return {
            "success": True,
            "category_id": str(metadata.get("category_id", "")),
            "category_name": metadata.get("category_name"),
            "metadata": metadata,
            "schema": schema,
            "cached": use_cache,
            "message": "Schema retrieved successfully"
        }
    except Exception as e:
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f"Error in get_ebay_schema_for_sku for {sku}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ebay/schemas/list", response_model=EbaySchemaListResponse)
def list_ebay_schemas():
    """List all cached eBay schemas"""
    try:
        schemas = ebay_schema.list_all_schemas()
        return EbaySchemaListResponse(
            success=True,
            count=len(schemas),
            schemas=schemas
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ebay/schemas/refresh", response_model=EbaySchemaRefreshResponse)
def refresh_ebay_schemas(request: EbaySchemaRefreshRequest):
    """Refresh eBay schemas from API"""
    try:
        result = ebay_schema.refresh_schemas(
            category_ids=request.category_ids,
            force=request.force
        )
        
        refreshed = result.get("refreshed", [])
        failed = result.get("failed", [])
        
        return EbaySchemaRefreshResponse(
            success=len(failed) == 0,
            refreshed_count=len(refreshed),
            failed_count=len(failed),
            details=refreshed + failed,
            message=f"Refreshed {len(refreshed)} schemas, {len(failed)} failed"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# eBay Field Enrichment Endpoints
# ============================================================

@app.post("/api/ebay/enrich", response_model=EbayEnrichResponse)
def enrich_ebay_fields(request: EbayEnrichRequest):
    """Enrich eBay fields for a single SKU using AI vision"""
    try:
        result = ebay_enrichment.enrich_ebay_fields(request.sku, force=request.force)
        
        return EbayEnrichResponse(
            success=result.get("success", False),
            sku=result.get("sku", request.sku),
            updated_fields=result.get("updated_fields", 0),
            missing_required=result.get("missing_required", []),
            message=result.get("message", "Enrichment completed"),
            fields=result.get("fields"),
            required_fields=result.get("required_fields"),
            optional_fields=result.get("optional_fields"),
            used_images=result.get("used_images", 0)
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/ebay/enrich/batch", response_model=EbayBatchEnrichResponse)
def enrich_ebay_fields_batch(request: EbayBatchEnrichRequest):
    """Enrich eBay fields for multiple SKUs"""
    try:
        result = ebay_enrichment.enrich_multiple_skus(request.skus, force=request.force)
        
        results = []
        for r in result.get("results", []):
            results.append(EbayEnrichResponse(**r))
        
        return EbayBatchEnrichResponse(
            success=result.get("success", False),
            total_count=result.get("total_count", 0),
            successful_count=result.get("successful_count", 0),
            failed_count=result.get("failed_count", 0),
            results=results,
            message=result.get("message", "Batch enrichment completed")
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/ebay/validate/{sku}", response_model=EbayValidationResponse)
def validate_ebay_fields(sku: str):
    """Validate eBay fields for SKU (check required fields are filled)"""
    try:
        result = ebay_enrichment.validate_ebay_fields(sku)
        
        return EbayValidationResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/ebay/fields/{sku}")
async def get_ebay_fields_for_sku(sku: str):
    """Get eBay fields for a SKU based on its category"""
    try:
        from app.repositories.sku_json_repo import read_sku_json
        from app.services import ebay_schema
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"Getting eBay fields for SKU: {sku}")
        product_json = read_sku_json(sku)
        if not product_json:
            logger.warning(f"No JSON found for SKU {sku}")
            return {
                "success": False,
                "message": f"No JSON found for SKU {sku}",
                "required_fields": {},
                "optional_fields": {}
            }
        
        # Try to get category from multiple possible locations
        category = None
        
        # Try top-level category field
        if "category" in product_json:
            category = product_json.get("category")
        
        # Try from Ebay Category section
        if not category and "Ebay Category" in product_json:
            ebay_cat = product_json.get("Ebay Category", {})
            if isinstance(ebay_cat, dict):
                category = ebay_cat.get("Category")
        
        # Try from AI Product Details
        if not category and "AI Product Details" in product_json:
            ai_details = product_json.get("AI Product Details", {})
            if isinstance(ai_details, dict):
                category = ai_details.get("category") or ai_details.get("Category")
        
        if not category:
            logger.warning(f"No category set for SKU {sku}")
            return {
                "success": False,
                "message": f"No category set for SKU {sku}",
                "required_fields": {},
                "optional_fields": {}
            }
        
        logger.info(f"Found category for {sku}: {category}")
        # Get schema by category name
        schema_data = await ebay_schema.get_schema_by_category_name(category)
        logger.info(f"Schema data keys: {schema_data.keys() if schema_data else 'None'}")
        
        if "error" in schema_data:
            logger.warning(f"Schema error for {sku}: {schema_data.get('error')}")
            # Fallback to old behavior - return current eBay fields without schema
            ebay_fields = product_json.get("eBay Fields", {})
            
            if isinstance(ebay_fields, dict):
                if "required" in ebay_fields or "optional" in ebay_fields:
                    required_fields = ebay_fields.get("required", {})
                    optional_fields = ebay_fields.get("optional", {})
                else:
                    required_fields = {}
                    optional_fields = ebay_fields
            else:
                required_fields = {}
                optional_fields = {}
            
            return {
                "success": True,
                "sku": sku,
                "category": category,
                "required_fields": required_fields,
                "optional_fields": optional_fields,
                "warning": schema_data.get("error")
            }
        
        # Get existing eBay fields from product JSON
        ebay_fields = product_json.get("eBay Fields", {})
        logger.info(f"Existing eBay fields for {sku}: {type(ebay_fields)} with keys {ebay_fields.keys() if isinstance(ebay_fields, dict) else 'N/A'}")
        
        # Flatten eBay fields if it has required/optional structure
        flat_ebay_fields = {}
        if isinstance(ebay_fields, dict):
            if "required" in ebay_fields or "optional" in ebay_fields:
                # New nested structure: {required: {...}, optional: {...}}
                flat_ebay_fields.update(ebay_fields.get("required", {}))
                flat_ebay_fields.update(ebay_fields.get("optional", {}))
            else:
                # Old flat structure: {fieldName: value, ...}
                flat_ebay_fields = ebay_fields
        
        logger.info(f"Flat eBay fields count for {sku}: {len(flat_ebay_fields)}")
        
        # Split schema fields into required and optional
        required_fields = {}
        optional_fields = {}
        
        # Get the schema - handle nested structure with _metadata
        schema_wrapper = schema_data.get("schema", {})
        logger.info(f"Schema wrapper keys: {schema_wrapper.keys() if isinstance(schema_wrapper, dict) else 'N/A'}")
        
        # If schema has _metadata, it's the new saved format - get the nested schema
        if "_metadata" in schema_wrapper:
            schema_structure = schema_wrapper.get("schema", {})
        else:
            schema_structure = schema_wrapper
        
        # Handle old format with "required" and "optional" keys
        if "required" in schema_structure and "optional" in schema_structure:
            logger.info(f"Using old schema format for {sku} - required: {len(schema_structure.get('required', []))}, optional: {len(schema_structure.get('optional', []))}")
            # Old format: {schema: {required: [...], optional: [...]}}
            for field in schema_structure.get("required", []):
                field_name = field.get("name", "")
                current_value = flat_ebay_fields.get(field_name, "")
                
                field_info = {
                    "name": field_name,
                    "value": current_value,
                    "description": field.get("description", ""),
                    "options": field.get("values", [])  # "values" in old format
                }
                required_fields[field_name] = field_info
            
            for field in schema_structure.get("optional", []):
                field_name = field.get("name", "")
                current_value = flat_ebay_fields.get(field_name, "")
                
                field_info = {
                    "name": field_name,
                    "value": current_value,
                    "description": field.get("description", ""),
                    "options": field.get("values", [])  # "values" in old format
                }
                optional_fields[field_name] = field_info
        else:
            # New format: direct list of fields
            logger.info(f"Using new schema format for {sku}")
            for field in schema_structure.get("fields", []):
                field_name = field.get("name") or field.get("aspect_name") or ""
                current_value = flat_ebay_fields.get(field_name, "")
                
                field_info = {
                    "name": field_name,
                    "value": current_value,
                    "description": field.get("description", ""),
                    "options": field.get("options", [])
                }
                
                if field.get("required"):
                    required_fields[field_name] = field_info
                else:
                    optional_fields[field_name] = field_info
        
        logger.info(f"Final result for {sku} - required_fields: {len(required_fields)}, optional_fields: {len(optional_fields)}")
        return {
            "success": True,
            "sku": sku,
            "category": category,
            "categoryId": schema_data.get("categoryId"),
            "required_fields": required_fields,
            "optional_fields": optional_fields
        }
    except Exception as e:
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f"Error in get_ebay_fields_for_sku for {sku}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/skus/{sku}/ebay-fields")
def save_ebay_fields_for_sku(sku: str, request: dict):
    """Save eBay fields to SKU JSON file"""
    try:
        from app.repositories.sku_json_repo import read_sku_json, write_sku_json
        
        product_json = read_sku_json(sku)
        if not product_json:
            raise HTTPException(status_code=404, detail=f"No JSON found for SKU {sku}")
        
        # Update eBay Fields with new structured format
        product_json["eBay Fields"] = {
            "required": request.get("required_fields", {}),
            "optional": request.get("optional_fields", {})
        }
        
        write_sku_json(sku, product_json)
        
        return {
            "success": True,
            "message": "eBay fields saved successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/skus/{sku}/ebay-images")
def get_ebay_image_orders(sku: str):
    """Get eBay image orders for a SKU"""
    try:
        from app.repositories.sku_json_repo import read_sku_json
        
        product_json = read_sku_json(sku)
        if not product_json:
            return {"orders": {}}
        
        # Get eBay Images array from JSON
        ebay_images = product_json.get("Images", {}).get("eBay Images", [])
        
        # Convert array to { filename: order } dict
        orders = {}
        for img in ebay_images:
            if isinstance(img, dict) and "filename" in img and "order" in img:
                orders[img["filename"]] = img["order"]
        
        return {"orders": orders}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/skus/{sku}/ebay-images")
def save_ebay_image_orders(sku: str, request: dict):
    """Save eBay image orders for a SKU"""
    try:
        from app.repositories.sku_json_repo import read_sku_json, write_sku_json
        
        product_json = read_sku_json(sku)
        if not product_json:
            raise HTTPException(status_code=404, detail=f"No JSON found for SKU {sku}")
        
        orders = request.get("orders", {})
        
        # Ensure Images section exists
        if "Images" not in product_json:
            product_json["Images"] = {}
        
        # Build eBay Images array from orders dict
        ebay_images = []
        for filename, order in orders.items():
            ebay_images.append({
                "filename": filename,
                "order": order,
                "eBay URL": ""  # Will be filled when uploaded to eBay
            })
        
        # Sort by order
        ebay_images.sort(key=lambda x: x["order"])
        
        product_json["Images"]["eBay Images"] = ebay_images
        
        write_sku_json(sku, product_json)
        
        return {
            "success": True,
            "message": "eBay image orders saved successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# eBay Listing Endpoints
# ============================================================

@app.post("/api/ebay/images/upload", response_model=ImageUploadResponse)
def upload_ebay_images(request: ImageUploadRequest):
    """Upload images to eBay Picture Services"""
    try:
        result = ebay_listing.upload_images_for_sku(
            sku=request.sku,
            max_images=request.max_images,
            force_reupload=request.force_reupload
        )
        
        return ImageUploadResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/ebay/manufacturer/lookup", response_model=ManufacturerLookupResponse)
def lookup_manufacturer(request: ManufacturerLookupRequest):
    """Lookup manufacturer information for brand"""
    try:
        manufacturer_info = ebay_listing.get_manufacturer_info(
            request.brand,
            force_refresh=request.force_refresh
        )
        
        if manufacturer_info:
            return ManufacturerLookupResponse(
                success=True,
                brand=request.brand,
                manufacturer_info=manufacturer_info,
                cached=not request.force_refresh,
                message="Manufacturer info retrieved"
            )
        else:
            return ManufacturerLookupResponse(
                success=False,
                brand=request.brand,
                manufacturer_info=None,
                cached=False,
                message="Manufacturer info not found"
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/ebay/listings/preview", response_model=ListingPreviewResponse)
def preview_ebay_listing(request: ListingPreviewRequest):
    """Preview eBay listing without creating it"""
    try:
        result = ebay_listing.preview_listing(
            sku=request.sku,
            price=request.price,
            condition_id=request.condition_id
        )
        
        return ListingPreviewResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/ebay/listings/create", response_model=CreateListingResponse)
def create_ebay_listing(request: CreateListingRequest):
    """Create eBay listing"""
    try:
        result = ebay_listing.create_listing(
            sku=request.sku,
            price=request.price,
            condition_id=request.condition_id,
            schedule_days=request.schedule_days,
            payment_policy=request.payment_policy,
            return_policy=request.return_policy,
            shipping_policy=request.shipping_policy,
            custom_description=request.custom_description,
            best_offer_enabled=request.best_offer_enabled,
            quantity=request.quantity,
            ebay_sku=request.ebay_sku
        )
        
        return CreateListingResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/ebay/listings/batch", response_model=BatchCreateListingResponse)
def create_ebay_listings_batch(request: BatchCreateListingRequest):
    """Create multiple eBay listings"""
    results = []
    successful = 0
    failed = 0
    
    for listing_req in request.listings:
        try:
            result = ebay_listing.create_listing(
                sku=listing_req.sku,
                price=listing_req.price,
                condition_id=listing_req.condition_id,
                schedule_days=listing_req.schedule_days,
                payment_policy=listing_req.payment_policy,
                return_policy=listing_req.return_policy,
                shipping_policy=listing_req.shipping_policy,
                custom_description=listing_req.custom_description,
                best_offer_enabled=listing_req.best_offer_enabled,
                quantity=listing_req.quantity
            )
            results.append(CreateListingResponse(**result))
            
            if result.get("success"):
                successful += 1
            else:
                failed += 1
                if request.stop_on_error:
                    break
        except Exception as e:
            results.append(CreateListingResponse(
                success=False,
                sku=listing_req.sku,
                message=f"Error: {str(e)}",
                errors=[str(e)]
            ))
            failed += 1
            if request.stop_on_error:
                break
    
    return BatchCreateListingResponse(
        success=successful > 0,
        total_count=len(request.listings),
        successful_count=successful,
        failed_count=failed,
        results=results,
        message=f"Created {successful} listings, {failed} failed"
    )


# ============================================================
# eBay Sync Endpoints
# ============================================================

@app.get("/api/skus/folder-images/status")
def get_folder_images_status():
    """Get folder images cache status"""
    last_update = get_folder_images_last_update()
    return {
        "last_update": last_update,
        "has_cache": last_update is not None
    }


@app.post("/api/skus/folder-images/compute")
def compute_folder_images():
    """Compute folder images for all SKUs with SSE progress updates"""
    def event_stream():
        for progress in compute_folder_images_for_all_skus():
            yield f"data: {json.dumps(progress)}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/api/skus/ebay-listings/status")
def get_ebay_listings_status():
    """Get eBay listings cache status"""
    last_update = get_ebay_listings_last_update()
    cache = read_ebay_cache()
    count = len(cache.get('listings', [])) if cache else 0
    return {
        "last_update": last_update,
        "has_cache": last_update is not None,
        "listings_count": count
    }


@app.post("/api/skus/ebay-listings/compute")
def compute_ebay_listings_endpoint():
    """Fetch eBay listings and update cache with SSE progress updates"""
    def event_stream():
        for progress in compute_ebay_listings():
            yield f"data: {json.dumps(progress)}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/api/ebay/sync/listings", response_model=SyncListingsResponse)
def sync_ebay_listings(request: SyncListingsRequest):
    """Fetch active eBay listings"""
    try:
        result = ebay_sync.get_active_listings(
            use_cache=request.use_cache,
            force_refresh=request.force_refresh
        )
        
        return SyncListingsResponse(
            success=result.get("success", False),
            total_listings=result.get("total_listings", 0),
            cached=result.get("cached", False),
            listings=result.get("listings", []),
            message=result.get("message", "")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ebay/sync/counts", response_model=ListingCountsResponse)
def get_ebay_listing_counts(use_cache: bool = Query(True)):
    """Get SKU listing counts"""
    try:
        result = ebay_sync.get_sku_listing_counts(use_cache=use_cache)
        
        return ListingCountsResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ebay/sync/status/{sku}", response_model=SyncStatusResponse)
def sync_listing_status(sku: str):
    """Sync listing status for specific SKU"""
    try:
        result = ebay_sync.sync_listing_status_for_sku(sku)
        
        return SyncStatusResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/ebay/sync/cache")
def clear_ebay_cache():
    """Clear eBay listings cache"""
    try:
        result = ebay_sync.clear_listings_cache()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))