from __future__ import annotations

from typing import List

from pydantic import BaseModel


class PromptItem(BaseModel):
    key: str
    text: str


class PromptViewItem(BaseModel):
    key: str
    label: str
    text: str


class PromptListRequest(BaseModel):
    prompts: List[PromptItem]


class PromptListResponse(BaseModel):
    model: str
    prompts: List[PromptViewItem]
