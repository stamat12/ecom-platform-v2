from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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