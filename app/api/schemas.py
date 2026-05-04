from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ImageOut(BaseModel):
    id: UUID
    status: str
    sha256: str
    bytes: int
    content_type: str
    created_at: datetime
    updated_at: datetime
    url: str | None = None
    error: str | None = None


class UploadResponse(BaseModel):
    image_id: UUID
    status: str


class TextSearchRequest(BaseModel):
    query: str
    top_k: int = 5


class SearchHit(BaseModel):
    image_id: UUID
    score: float
    url: str | None = None


class SearchResponse(BaseModel):
    hits: list[SearchHit]


class DedupeRequest(BaseModel):
    threshold: float = 0.97
    top_k: int = 10
    limit_images: int = 200


class DedupePair(BaseModel):
    a: UUID
    b: UUID
    score: float


class DedupeResponse(BaseModel):
    pairs: list[DedupePair]

