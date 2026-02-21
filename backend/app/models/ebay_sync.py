"""
Pydantic models for eBay listing synchronization
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional


class ProfitAnalysis(BaseModel):
    """Profit analysis for a listing"""
    selling_price_brutto: float
    selling_price_netto: float
    payment_fee: float
    sales_commission: float
    sales_commission_percentage: float
    shipping_costs_net: float
    total_cost_net: float
    net_profit: float
    net_profit_margin_percent: float


class EbayListingInfo(BaseModel):
    """Single eBay listing information"""
    item_id: str
    sku: str
    title: str
    marketplace: str
    view_url: Optional[str] = None
    site: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    quantity_total: Optional[int] = None
    quantity_available: Optional[int] = None
    quantity_sold: Optional[int] = None
    listing_status: Optional[str] = None
    listing_type: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    condition_id: Optional[int] = None
    condition_name: Optional[str] = None
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    best_offer_enabled: Optional[bool] = None
    primary_image_url: Optional[str] = None
    image_urls: Optional[List[str]] = None
    profit_analysis: Optional[ProfitAnalysis] = None


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
