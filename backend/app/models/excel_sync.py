from pydantic import BaseModel, Field
from typing import List


class ExcelSheetInfo(BaseModel):
    sheet_name: str
    columns: List[str]


class ExcelToDbSyncRequest(BaseModel):
    sheets: List[ExcelSheetInfo] = Field(description="List of sheets and columns to sync")
    update_category_mapping: bool = Field(default=False, description="Also refresh category_mapping.json from Excel category sheet")


class ExcelToDbSyncResponse(BaseModel):
    success: bool
    message: str
    results: List[dict] = Field(default_factory=list)
