"""
Pydantic models for eBay field enrichment operations
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional


class EbayEnrichRequest(BaseModel):
    """Request to enrich eBay fields for a SKU"""
    sku: str
    force: bool = False  # Force re-enrichment even if fields exist


class EbayBatchEnrichRequest(BaseModel):
    """Request to enrich multiple SKUs"""
    skus: List[str]
    force: bool = False


class EbayEnrichResponse(BaseModel):
    """Response for eBay field enrichment"""
    success: bool
    sku: str
    updated_fields: int = 0
    missing_required: List[str] = Field(default_factory=list)
    message: str
    fields: Optional[Dict[str, str]] = None  # All fields (required + optional)
    required_fields: Optional[Dict[str, str]] = None
    optional_fields: Optional[Dict[str, str]] = None
    used_images: int = 0


class EbayBatchEnrichResponse(BaseModel):
    """Response for batch enrichment"""
    success: bool
    total_count: int
    successful_count: int
    failed_count: int
    results: List[EbayEnrichResponse]
    message: str


class EbayValidationRequest(BaseModel):
    """Request to validate eBay fields"""
    sku: str


class EbayValidationResponse(BaseModel):
    """Response for eBay field validation"""
    sku: str
    valid: bool
    missing_required: List[str] = Field(default_factory=list)
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    total_required: int = 0
    filled_required: int = 0
    total_optional: int = 0
    filled_optional: int = 0
    message: str
