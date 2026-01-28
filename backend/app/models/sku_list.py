from pydantic import BaseModel
from typing import List, Dict, Any
from enum import Enum


class ColumnFilter(BaseModel):
    """Filter for a single column"""
    column: str
    value: str
    operator: str = "contains"  # contains, equals, starts_with, ends_with


class SkuListRequest(BaseModel):
    """Request model for SKU list with filters"""
    page: int = 1
    page_size: int = 50
    columns: List[str] | None = None
    filters: List[ColumnFilter] | None = None


class SkuItem(BaseModel):
    """A single SKU record"""
    pass  # Dynamic - will accept any fields


class SkuListResponse(BaseModel):
    """Stable API response for SKU list"""
    page: int
    page_size: int
    total: int
    items: List[Dict[str, Any]]
    available_columns: List[str] | None = None


class SkuColumnsResponse(BaseModel):
    """Available columns for filtering and selection"""
    columns: List[str]
    total_columns: int
    default_columns: List[str]

class ImageInfo(BaseModel):
    """Image information with URLs"""
    filename: str
    classification: str | None = None
    is_main: bool = False
    is_ebay: bool = False
    meta: Dict[str, Any] = {}
    thumb_url: str
    preview_url: str
    original_url: str
    source: str | None = None


class SkuImagesResponse(BaseModel):
    """Stable API response for SKU images"""
    sku: str
    folder_found: bool
    count: int
    main_images: List[str] = []
    ebay_images: List[str] = []
    images: List[ImageInfo]


class SkuFilterState(BaseModel):
    """Persistent filter state for the SKU list page"""
    profile_id: str = "default"
    selected_columns: List[str] = []
    column_filters: Dict[str, Any] = {}
    page_size: int = 50
    column_widths: Dict[str, int] = {}

class SkuFilterStateResponse(BaseModel):
    """Response wrapper for filter state (keeps schema stable)"""
    profile_id: str
    selected_columns: List[str]
    column_filters: Dict[str, Any]
    page_size: int
    column_widths: Dict[str, int]


class ColumnType(str, Enum):
    string = "string"
    number = "number"
    date = "date"
    boolean = "boolean"
    enum = "enum"


class ColumnMeta(BaseModel):
    name: str
    type: ColumnType
    operators: List[str]
    enum_values: List[str] | None = None


class SkuColumnMetaResponse(BaseModel):
    columns: List[ColumnMeta]
    total_columns: int


class FilterCondition(BaseModel):
    """Type-aware filter condition for a single column"""
    column: str
    type: ColumnType
    operator: str
    value: Any | None = None
    value2: Any | None = None  # used for between
    values: List[str] | None = None  # used for in/not_in


class DistinctValuesResponse(BaseModel):
    """Distinct values for a column (for multi-select UIs)"""
    column: str
    values: List[str]
    total_unique: int
    limited: bool

