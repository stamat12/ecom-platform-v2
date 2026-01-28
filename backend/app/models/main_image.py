from pydantic import BaseModel
from typing import List


class MainImageRequest(BaseModel):
    """Request to mark/unmark images as main"""
    sku: str
    filenames: List[str]


class MainImageResponse(BaseModel):
    """Response after marking/unmarking main images"""
    success: bool
    message: str
    sku: str
    processed_count: int


class BatchMainImageRequest(BaseModel):
    """Request to mark/unmark images as main across multiple SKUs"""
    images: List[dict]  # [{"sku": str, "filename": str}, ...]
    action: str  # "mark" or "unmark"


class BatchMainImageResponse(BaseModel):
    """Response after batch main image operation"""
    success: bool
    message: str
    processed_count: int
    results: List[dict]
