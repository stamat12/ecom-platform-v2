from pydantic import BaseModel
from typing import List, Optional


class ImageReference(BaseModel):
    sku: str
    filename: str


class BatchImageEnhanceRequest(BaseModel):
    images: List[ImageReference]
    prompt_key: str
    upscale: bool = True
    target_size_mb: float = 8.0
    gemini_model: Optional[str] = None


class BatchImageEnhanceResponse(BaseModel):
    success: bool
    message: str
    processed_count: int
    prompt_key: str
    upscale: bool = False
    target_size_mb: float = 8.0
    results: List[dict]


class BatchImageUpscaleRequest(BaseModel):
    images: List[ImageReference]
    scale: int = 4


class BatchImageUpscaleResponse(BaseModel):
    success: bool
    message: str
    processed_count: int
    results: List[dict]
