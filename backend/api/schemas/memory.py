"""Memory API schemas."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class MemoryType(StrEnum):
    USER = "user"
    PROJECT = "project"
    CONVERSATION_SUMMARY = "conversation_summary"


class MemoryScope(StrEnum):
    USER = "user"
    PROJECT = "project"
    CONVERSATION = "conversation"


class MemoryRead(BaseModel):
    id: str
    memory_type: MemoryType
    scope: MemoryScope
    project_id: str | None
    conversation_id: str | None
    title: str
    content: str
    summary: str | None
    source: str
    source_message_id: str | None
    importance: int
    pinned: bool
    enabled: bool
    tags: list[str]
    metadata: dict[str, Any]
    last_used_at: datetime | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime


class MemoryListResponse(BaseModel):
    items: list[MemoryRead]
    total: int


class MemoryCreateRequest(BaseModel):
    memory_type: MemoryType = MemoryType.USER
    scope: MemoryScope = MemoryScope.USER
    title: str = Field(min_length=1, max_length=180)
    content: str = Field(min_length=1, max_length=8000)
    project_id: str | None = Field(default=None, max_length=120)
    conversation_id: str | None = None
    source_message_id: str | None = None
    importance: int = Field(default=3, ge=1, le=5)
    pinned: bool = False
    enabled: bool = True
    expires_at: datetime | None = None
    tags: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("title", "content")
    @classmethod
    def trim_required(cls, value: str) -> str:
        candidate = value.strip()
        if not candidate:
            raise ValueError("field cannot be empty")
        return candidate


class MemoryPatchRequest(BaseModel):
    title: str | None = Field(default=None, max_length=180)
    content: str | None = Field(default=None, max_length=8000)
    importance: int | None = Field(default=None, ge=1, le=5)
    pinned: bool | None = None
    enabled: bool | None = None
    expires_at: datetime | None = None
    tags: list[str] | None = Field(default=None, max_length=20)


class MemorySearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=20)
    memory_type: MemoryType | None = None

    @field_validator("query")
    @classmethod
    def trim_query(cls, value: str) -> str:
        candidate = value.strip()
        if not candidate:
            raise ValueError("query cannot be empty")
        return candidate


class MemorySearchResult(BaseModel):
    memory: MemoryRead
    relevance: float


class MemorySearchResponse(BaseModel):
    items: list[MemorySearchResult]
    diagnostics: dict[str, Any]


class MemoryExportResponse(BaseModel):
    exported_at: datetime
    items: list[MemoryRead]
