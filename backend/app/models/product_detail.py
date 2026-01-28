"""
Pydantic models for product detail endpoints.
Provides stable API schema independent of JSON storage format.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ProductDetailField(BaseModel):
    """A single field in a product detail category."""
    name: str = Field(..., description="Field name (e.g., 'Brand', 'Color')")
    value: str = Field(default="", description="Field value")
    is_highlighted: bool = Field(
        default=False,
        description="Whether this field should be highlighted in UI (e.g., important fields)"
    )


class ProductDetailCategory(BaseModel):
    """A category of product fields (e.g., 'Invoice Data', 'Product Info')."""
    name: str = Field(..., description="Category name")
    fields: List[ProductDetailField] = Field(
        default_factory=list,
        description="List of fields in this category"
    )


class ProductDetailResponse(BaseModel):
    """Complete product detail response with all categories and fields."""
    sku: str = Field(..., description="Product SKU")
    exists: bool = Field(..., description="Whether product JSON exists")
    categories: List[ProductDetailCategory] = Field(
        default_factory=list,
        description="List of categories with their fields"
    )
    
    # Summary statistics
    total_categories: int = Field(default=0, description="Total number of categories")
    total_fields: int = Field(default=0, description="Total number of fields")
    filled_fields: int = Field(default=0, description="Number of non-empty fields")
    completion_percentage: float = Field(
        default=0.0,
        description="Percentage of filled fields (0-100)"
    )


class UpdateProductDetailRequest(BaseModel):
    """Request to update product detail fields."""
    sku: str = Field(..., description="Product SKU")
    updates: Dict[str, Dict[str, str]] = Field(
        ...,
        description="Updates in format {'Category Name': {'Field Name': 'New Value'}}"
    )


class UpdateProductDetailResponse(BaseModel):
    """Response after updating product details."""
    success: bool = Field(..., description="Whether update succeeded")
    message: str = Field(..., description="Result message")
    updated_fields: int = Field(default=0, description="Number of fields updated")
