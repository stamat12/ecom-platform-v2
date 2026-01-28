"""
Pydantic models for eBay schema operations
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any


class EbayFieldValue(BaseModel):
    """Single field value option"""
    name: str
    values: Optional[List[str]] = None  # Allowed values, None if free text


class EbaySchema(BaseModel):
    """eBay category schema"""
    required: List[EbayFieldValue] = Field(default_factory=list)
    optional: List[EbayFieldValue] = Field(default_factory=list)


class EbaySchemaMetadata(BaseModel):
    """Metadata for eBay schema"""
    category_name: str
    category_id: str
    marketplace: str = "EBAY_DE"
    fees: Optional[Dict[str, float]] = None


class EbaySchemaResponse(BaseModel):
    """Response for schema retrieval"""
    success: bool
    category_id: str
    category_name: Optional[str] = None
    metadata: Optional[EbaySchemaMetadata] = None
    schema: Optional[EbaySchema] = None
    cached: bool = False
    message: Optional[str] = None


class EbaySchemaListResponse(BaseModel):
    """Response for listing all cached schemas"""
    success: bool
    count: int
    schemas: List[Dict[str, Any]]  # List of {category_id, category_name, cached_at}


class EbaySchemaRefreshRequest(BaseModel):
    """Request to refresh schemas"""
    category_ids: Optional[List[str]] = None  # If None, refresh all
    force: bool = False  # Force refresh even if cached


class EbaySchemaRefreshResponse(BaseModel):
    """Response for schema refresh"""
    success: bool
    refreshed_count: int
    failed_count: int
    details: List[Dict[str, Any]]  # List of {category_id, status, message}
    message: str
