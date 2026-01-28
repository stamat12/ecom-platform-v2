from pydantic import BaseModel, Field
from typing import Dict, Any


class ImageRotateRequest(BaseModel):
    """Request to rotate an image"""
    sku: str
    filename: str
    degrees: int = Field(..., description="Rotation degrees: 90, 180, or 270")


class ImageRotateResponse(BaseModel):
    """Response after rotating an image"""
    success: bool
    message: str
    sku: str
    filename: str
    degrees: int


class JsonStatusResponse(BaseModel):
    """Response indicating if JSON file exists for a SKU"""
    sku: str
    json_exists: bool


class JsonGenerateRequest(BaseModel):
    """Request to generate JSON for a SKU (optional body)"""
    pass  # SKU is in URL path, not in body


class JsonGenerateResponse(BaseModel):
    """Response after generating JSON for a SKU"""
    success: bool
    message: str
    sku: str


class SkuDetailResponse(BaseModel):
    """Stable response for SKU detail endpoint"""
    sku: str
    data: Dict[str, Any] = {}
    exists: bool
