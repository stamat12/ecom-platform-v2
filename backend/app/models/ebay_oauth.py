"""
Pydantic models for eBay OAuth helper endpoints
"""
from typing import Optional
from pydantic import BaseModel, Field


class EbayOAuthExchangeRequest(BaseModel):
    """Request to exchange auth code for refresh token"""
    code: str = Field(min_length=1)
    redirect_uri: Optional[str] = None


class EbayOAuthExchangeResponse(BaseModel):
    """Response containing refresh token and expiry"""
    success: bool
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    message: str
