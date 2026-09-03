from __future__ import annotations

import re
from typing import Annotated
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator

STICKER_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
ALLOWED_IMAGE_SCHEMES = {"http", "https"}


class Sticker(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=100)
    image_url: str = Field(min_length=1, max_length=2048)
    tags: list[str] = Field(min_length=1, max_length=30)
    description: str = Field(min_length=1, max_length=500)
    emotion: list[str] = Field(min_length=1, max_length=20)
    usage: str = Field(min_length=1, max_length=500)

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if not STICKER_ID_RE.fullmatch(value):
            raise ValueError("id 只能包含字母、数字、下划线和连字符，且长度不超过 64")
        return value

    @field_validator("tags", "emotion")
    @classmethod
    def normalize_string_lists(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        for value in values:
            item = value.strip()
            if item and item not in cleaned:
                cleaned.append(item)
        if not cleaned:
            raise ValueError("列表不能为空")
        return cleaned

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, value: str) -> str:
        if value.startswith("${PUBLIC_BASE_URL}/") or value.startswith("/"):
            return value
        parsed = urlparse(value)
        if parsed.scheme not in ALLOWED_IMAGE_SCHEMES or not parsed.netloc:
            raise ValueError("image_url 必须是 http(s) URL、站内绝对路径或 PUBLIC_BASE_URL 模板")
        return value


class StickerView(Sticker):
    markdown: str


class SearchResponse(BaseModel):
    stickers: list[StickerView]
    match_count: int
    assistant_hint: str


class GetResponse(BaseModel):
    sticker: StickerView
    assistant_hint: str


class ListResponse(BaseModel):
    stickers: list[StickerView]
    total: int


class AddResponse(BaseModel):
    sticker: StickerView
    message: str


class ChatGPTFile(BaseModel):
    """Exact file object shape required by ChatGPT's openai/fileParams contract."""

    model_config = ConfigDict(extra="forbid")

    download_url: str
    file_id: str
    mime_type: str | None = None
    file_name: str | None = None


Limit = Annotated[int, Field(ge=1, le=3)]
