from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class InventoryImportRequest(BaseModel):
    skus: Optional[List[str]] = Field(default=None, description="Optional list of SKUs to import")
    append_missing: bool = Field(default=False, description="Append missing SKUs to the sheet")


class InventoryImportResponse(BaseModel):
    success: bool
    processed: int = 0
    updated: int = 0
    appended: int = 0
    message: str