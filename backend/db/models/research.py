"""Live research persistence models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base
from backend.db.types import id_column, utc_created_column, utc_updated_column


class ResearchSession(Base):
    __tablename__ = "research_sessions"

    id: Mapped[str] = id_column()
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    answer: Mapped[str] = mapped_column(Text, default="", nullable=False)
    official_only: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    filters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    diagnostics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = utc_created_column()
    updated_at: Mapped[datetime] = utc_updated_column()


class ResearchSource(Base):
    __tablename__ = "research_sources"

    id: Mapped[str] = id_column()
    session_id: Mapped[str | None] = mapped_column(
        ForeignKey("research_sessions.id"), nullable=True, index=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    citation_id: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_url: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, default="", nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), default="web", nullable=False)
    reliability: Mapped[str] = mapped_column(String(80), default="unknown", nullable=False)
    excerpt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    content_checksum: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    retrieved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = utc_created_column()
    updated_at: Mapped[datetime] = utc_updated_column()


class ResearchCacheEntry(Base):
    __tablename__ = "research_cache_entries"
    __table_args__ = (UniqueConstraint("normalized_url", name="uq_research_cache_normalized_url"),)

    id: Mapped[str] = id_column()
    normalized_url: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, default="", nullable=False)
    content_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    excerpt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status_code: Mapped[int | None] = mapped_column(nullable=True)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    retrieved_at: Mapped[datetime] = mapped_column(nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(nullable=False, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = utc_created_column()
    updated_at: Mapped[datetime] = utc_updated_column()
