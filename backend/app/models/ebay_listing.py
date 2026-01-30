"""
Pydantic models for eBay listing operations
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime


class ImageUploadRequest(BaseModel):
    """Request to upload images to eBay Picture Services"""
    sku: str
    max_images: int = Field(default=12, ge=1, le=24)
    force_reupload: bool = False  # Force re-upload even if URLs cached


class ImageUploadResponse(BaseModel):
    """Response for image upload"""
    success: bool
    sku: str
    uploaded_count: int
    cached_count: int
    total_count: int
    urls: List[str]
    message: str


class ManufacturerInfo(BaseModel):
    """Manufacturer contact information"""
    company_name: str = Field(alias="CompanyName")
    street1: str = Field(alias="Street1")
    street2: Optional[str] = Field(default=None, alias="Street2")
    city: str = Field(alias="CityName")
    state: Optional[str] = Field(default=None, alias="StateOrProvince")
    postal_code: str = Field(alias="PostalCode")
    country: str = Field(default="DE", alias="Country")
    phone: Optional[str] = Field(default=None, alias="Phone")
    email: Optional[str] = Field(default=None, alias="Email")
    contact_url: Optional[str] = Field(default=None, alias="ContactURL")
    
    class Config:
        populate_by_name = True


class ManufacturerLookupRequest(BaseModel):
    """Request to lookup manufacturer info"""
    brand: str
    force_refresh: bool = False


class ManufacturerLookupResponse(BaseModel):
    """Response for manufacturer lookup"""
    success: bool
    brand: str
    manufacturer_info: Optional[Dict[str, Any]] = None
    cached: bool = False
    message: str


class CreateListingRequest(BaseModel):
    """Request to create eBay listing"""
    sku: str
    ebay_sku: Optional[str] = Field(default=None, description="SKU to use for eBay listing (if different from source SKU)")
    price: float = Field(gt=0)
    condition_id: Optional[int] = Field(default=None, description="eBay condition ID (e.g., 1000=New)")
    schedule_days: int = Field(default=14, ge=0, le=30, description="Days to schedule listing in future")
    payment_policy: Optional[str] = None
    return_policy: Optional[str] = None
    shipping_policy: Optional[str] = None
    custom_description: Optional[str] = None
    best_offer_enabled: bool = True
    quantity: int = Field(default=1, ge=1)


class ListingPreviewRequest(BaseModel):
    """Request to preview listing without creating"""
    sku: str
    price: float = Field(gt=0)
    condition_id: Optional[int] = None


class CreateListingResponse(BaseModel):
    """Response for listing creation"""
    success: bool
    sku: str
    item_id: Optional[str] = None
    title: Optional[str] = None
    category_id: Optional[str] = None
    price: Optional[float] = None
    scheduled_time: Optional[str] = None
    image_count: int = 0
    has_manufacturer_info: bool = False
    message: str
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class ListingPreviewResponse(BaseModel):
    """Response for listing preview"""
    success: bool
    sku: str
    title: str
    description_html: str
    category_id: str
    category_name: Optional[str] = None
    price: float
    condition_id: int
    condition_text: Optional[str] = None
    image_count: int
    image_urls: List[str]
    item_specifics: Dict[str, Any]
    has_manufacturer_info: bool
    missing_required_fields: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    message: str


class BatchCreateListingRequest(BaseModel):
    """Request to create multiple listings"""
    listings: List[CreateListingRequest]
    stop_on_error: bool = False


class BatchCreateListingResponse(BaseModel):
    """Response for batch listing creation"""
    success: bool
    total_count: int
    successful_count: int
    failed_count: int
    results: List[CreateListingResponse]
    message: str
