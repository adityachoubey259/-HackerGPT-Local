"""RAG domain models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class DocumentStatus(StrEnum):
    PENDING = "pending"
    INDEXING = "indexing"
    INDEXED = "indexed"
    FAILED = "failed"
    UNSUPPORTED = "unsupported"
    DELETED = "deleted"


class IngestionJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class ParsedSection(BaseModel):
    text: str
    page_number: int | None = None
    heading: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ParsedDocument(BaseModel):
    source_id: str
    file_name: str
    source_path: str | None = None
    mime_type: str | None = None
    title: str | None = None
    content: str
    sections: list[ParsedSection] = Field(default_factory=list)
    parser: str
    checksum: str
    size_bytes: int
    metadata: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class DocumentChunkDraft(BaseModel):
    text: str
    chunk_index: int
    page_number: int | None = None
    section: str | None = None
    source_path: str | None = None
    checksum: str
    token_count: int
    character_count: int
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EmbeddedText(BaseModel):
    text: str
    checksum: str
    vector: list[float]
    provider: str
    model: str
    dimension: int


class RetrievalFilter(BaseModel):
    tags: list[str] = Field(default_factory=list)
    document_ids: list[str] = Field(default_factory=list)
    project_id: str | None = None


class RetrievalResult(BaseModel):
    chunk_id: str
    document_id: str
    citation_id: str
    text: str
    score: float
    lexical_score: float = 0.0
    vector_score: float | None = None
    reranker_score: float | None = None
    file_name: str
    source_path: str | None = None
    page_number: int | None = None
    section: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Citation(BaseModel):
    citation_id: str
    chunk_id: str
    document_id: str
    file_name: str
    source_path: str | None = None
    page_number: int | None = None
    section: str | None = None
    score: float | None = None


class RagContextPack(BaseModel):
    context_text: str
    results: list[RetrievalResult]
    citations: list[Citation]
    estimated_tokens: int
    diagnostics: dict[str, Any] = Field(default_factory=dict)


class IngestionCandidate(BaseModel):
    path: Path
    display_name: str
    size_bytes: int
    checksum: str
    mime_type: str | None = None


class KnowledgeStats(BaseModel):
    document_count: int
    chunk_count: int
    embedding_provider: str
    embedding_model: str
    vector_store: str
    vector_store_status: str
    updated_at: datetime | None = None
