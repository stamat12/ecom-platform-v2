from pydantic import BaseModel
from typing import List, Optional


class ImageEnhanceRequest(BaseModel):
    sku: str
    filenames: List[str]
    prompt_key: str


class ImageEnhanceResponse(BaseModel):
    success: bool
    message: str
    sku: str
    prompt_key: str
    processed_count: int
    generated: List[str]
    errors: List[str]


class ImageUpscaleRequest(BaseModel):
    sku: str
    filenames: List[str]
    scale: int = 4


class ImageUpscaleResponse(BaseModel):
    success: bool
    message: str
    sku: str
    processed_count: int
    upscaled: List[str]
    errors: List[str]


class PromptInfo(BaseModel):
    key: str
    label: str


class ImagePromptsResponse(BaseModel):
    success: bool
    prompts: List[PromptInfo]
