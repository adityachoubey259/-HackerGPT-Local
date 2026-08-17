"""Knowledge document persistence models."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base
from backend.db.types import id_column, utc_created_column, utc_updated_column

if TYPE_CHECKING:
    from backend.db.models.user import User


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = id_column()
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="upload")
    source_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(180), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    parser: Mapped[str | None] = mapped_column(String(80), nullable=True)
    title: Mapped[str | None] = mapped_column(String(240), nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, default=dict, nullable=False
    )
    failure_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    failure_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    indexed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = utc_created_column()
    updated_at: Mapped[datetime] = utc_updated_column()

    user: Mapped[User] = relationship("User")
    chunks: Mapped[list[DocumentChunk]] = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[str] = id_column()
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    citation_id: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section: Mapped[str | None] = mapped_column(String(240), nullable=True)
    source_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    character_count: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding_provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(180), nullable=True)
    embedding_dimension: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, default=dict, nullable=False
    )
    created_at: Mapped[datetime] = utc_created_column()

    document: Mapped[Document] = relationship("Document", back_populates="chunks")


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[str] = id_column()
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    document_id: Mapped[str | None] = mapped_column(
        ForeignKey("documents.id"), nullable=True, index=True
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", index=True)
    total_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processed_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chunks_indexed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    failure_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, default=dict, nullable=False
    )
    created_at: Mapped[datetime] = utc_created_column()
    updated_at: Mapped[datetime] = utc_updated_column()


class EmbeddingCache(Base):
    __tablename__ = "embedding_cache"

    id: Mapped[str] = id_column()
    content_checksum: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    model: Mapped[str] = mapped_column(String(180), nullable=False)
    dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    vector: Mapped[list[float]] = mapped_column(JSON, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, default=dict, nullable=False
    )
    created_at: Mapped[datetime] = utc_created_column()


class MessageRetrieval(Base):
    __tablename__ = "message_retrievals"

    id: Mapped[str] = id_column()
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id"), nullable=False, index=True)
    chunk_id: Mapped[str | None] = mapped_column(
        ForeignKey("document_chunks.id"), nullable=True, index=True
    )
    memory_id: Mapped[str | None] = mapped_column(ForeignKey("memories.id"), nullable=True)
    citation_id: Mapped[str] = mapped_column(String(40), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    score: Mapped[float | None] = mapped_column(nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, default=dict, nullable=False
    )
    created_at: Mapped[datetime] = utc_created_column()
