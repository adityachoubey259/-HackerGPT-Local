"""Knowledge and RAG API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from backend.rag.models import DocumentStatus, IngestionJobStatus


class DocumentRead(BaseModel):
    id: str
    name: str
    source: str
    source_path: str | None
    mime_type: str | None
    size_bytes: int
    checksum: str
    status: DocumentStatus
    parser: str | None
    title: str | None
    tags: list[str]
    metadata: dict[str, Any]
    failure_code: str | None
    failure_message: str | None
    indexed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DocumentChunkRead(BaseModel):
    id: str
    document_id: str
    chunk_index: int
    citation_id: str
    text: str
    page_number: int | None
    section: str | None
    token_count: int
    character_count: int
    tags: list[str]
    metadata: dict[str, Any]
    created_at: datetime


class IngestionJobRead(BaseModel):
    id: str
    document_id: str | None
    source: str
    status: IngestionJobStatus
    total_files: int
    processed_files: int
    chunks_indexed: int
    failure_code: str | None
    failure_message: str | None
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class KnowledgeListResponse(BaseModel):
    items: list[DocumentRead]
    total: int


class DocumentDetailResponse(BaseModel):
    document: DocumentRead
    chunks: list[DocumentChunkRead]


class IngestPathRequest(BaseModel):
    path: str = Field(min_length=1, max_length=2000)
    tags: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("path")
    @classmethod
    def trim_path(cls, value: str) -> str:
        candidate = value.strip()
        if not candidate:
            raise ValueError("path cannot be empty")
        return candidate


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    limit: int = Field(default=5, ge=1, le=20)
    document_ids: list[str] = Field(default_factory=list, max_length=50)
    tags: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("query")
    @classmethod
    def trim_query(cls, value: str) -> str:
        candidate = value.strip()
        if not candidate:
            raise ValueError("query cannot be empty")
        return candidate


class KnowledgeSearchResult(BaseModel):
    chunk_id: str
    document_id: str
    citation_id: str
    text: str
    score: float
    file_name: str
    source_path: str | None
    page_number: int | None
    section: str | None
    metadata: dict[str, Any]


class KnowledgeSearchResponse(BaseModel):
    items: list[KnowledgeSearchResult]
    citations: list[dict[str, Any]]
    diagnostics: dict[str, Any]


class KnowledgeStatsResponse(BaseModel):
    document_count: int
    chunk_count: int
    embedding_provider: str
    embedding_model: str
    vector_store: str
    vector_store_status: str
