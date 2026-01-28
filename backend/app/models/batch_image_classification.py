from pydantic import BaseModel
from typing import List


class ImageReference(BaseModel):
    sku: str
    filename: str


class BatchImageClassificationRequest(BaseModel):
    images: List[ImageReference]
    classification_type: str


class BatchImageClassificationResponse(BaseModel):
    success: bool
    message: str
    processed_count: int
    classification_type: str
    results: List[dict]  # [{sku: str, filename: str, success: bool, error: str | None}]
