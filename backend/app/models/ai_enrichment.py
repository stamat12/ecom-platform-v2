"""Pydantic models for AI enrichment endpoints."""

from pydantic import BaseModel
from typing import Dict, List, Optional


class EnrichSingleRequest(BaseModel):
    """Request to enrich a single SKU."""
    sku: str


class EnrichSingleResponse(BaseModel):
    """Response from enriching a single SKU."""
    success: bool
    sku: str
    updated_fields: Optional[int] = None
    message: str
    data: Optional[Dict[str, str]] = None


class EnrichBatchRequest(BaseModel):
    """Request to enrich multiple SKUs."""
    skus: List[str]


class EnrichBatchResponse(BaseModel):
    """Response from batch enrichment."""
    success: bool
    total: int
    succeeded: int
    failed: int
    results: Dict[str, Dict]


class AIConfigResponse(BaseModel):
    """Response with current AI configuration."""
    model: str
    fields: List[str]
    prompt_preview: str  # First 200 chars of prompt for display
