"""Live research API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ResearchStatusResponse(BaseModel):
    enabled: bool
    search_enabled: bool
    provider: str
    configured: bool
    allowed_domains: list[str]
    blocked_domains: list[str]
    max_results: int
    cache_ttl_seconds: int
    official_sources_preferred: bool
    private_networks_blocked: bool


class ResearchRunRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    max_results: int | None = Field(default=None, ge=1, le=25)
    official_only: bool = False


class ResearchRetrieveRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2000)
    use_cache: bool = True


class ResearchSourceRead(BaseModel):
    id: str
    citation_id: str
    url: str
    normalized_url: str
    domain: str
    title: str
    source_type: str
    reliability: str
    excerpt: str
    content_checksum: str | None
    retrieved_at: datetime | None
    metadata: dict[str, Any]
    created_at: datetime


class ResearchSessionRead(BaseModel):
    id: str
    query: str
    status: str
    provider: str | None
    answer: str
    official_only: bool
    filters: dict[str, Any]
    diagnostics: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ResearchRunResponse(BaseModel):
    session: ResearchSessionRead
    sources: list[ResearchSourceRead]


class ResearchHistoryResponse(BaseModel):
    items: list[ResearchSessionRead]
    total: int


class RetrievedPageResponse(BaseModel):
    url: str
    normalized_url: str
    domain: str
    title: str
    excerpt: str
    content_checksum: str
    retrieved_at: datetime
    from_cache: bool
    diagnostics: dict[str, Any]
