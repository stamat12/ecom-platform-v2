"""
Pydantic models for eBay listing synchronization
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional


class EbayListingInfo(BaseModel):
    """Single eBay listing information"""
    item_id: str
    sku: str
    title: str
    marketplace: str
    view_url: Optional[str] = None


class SyncListingsRequest(BaseModel):
    """Request to sync eBay listings"""
    use_cache: bool = True
    force_refresh: bool = False


class SyncListingsResponse(BaseModel):
    """Response for listings sync"""
    success: bool
    total_listings: int
    cached: bool
    listings: List[EbayListingInfo]
    message: str


class ListingCountsResponse(BaseModel):
    """Response for SKU listing counts"""
    success: bool
    total_skus: int
    total_listings: int
    sku_counts: Dict[str, int]  # SKU -> count
    cached: bool
    message: str


class SyncStatusRequest(BaseModel):
    """Request to sync listing status for SKU"""
    sku: str


class SyncStatusResponse(BaseModel):
    """Response for status sync"""
    success: bool
    sku: str
    listing_count: int
    updated: bool
    message: str
