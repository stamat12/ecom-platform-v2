"""Pydantic models for image classification operations."""
from pydantic import BaseModel, Field
from typing import List, Optional


class ImageClassificationRequest(BaseModel):
    """Request to classify images"""
    sku: str
    filenames: List[str] = Field(..., description="List of image filenames to classify")
    classification_type: str = Field(..., description="Classification type: phone, stock, or enhanced")


class ImageClassificationResponse(BaseModel):
    """Response after classifying images"""
    success: bool
    message: str
    sku: str
    processed_count: int
    classification_type: str


class ImageClassificationStatus(BaseModel):
    """Status of an image's classification"""
    filename: str
    classification: Optional[str] = Field(None, description="Type: phone, stock, enhanced, or None if unclassified")
