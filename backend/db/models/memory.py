"""Long-term memory persistence models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base
from backend.db.types import id_column, utc_created_column, utc_updated_column


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[str] = id_column()
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    memory_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(40), nullable=False, default="user", index=True)
    project_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    conversation_id: Mapped[str | None] = mapped_column(
        ForeignKey("conversations.id"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="manual")
    source_message_id: Mapped[str | None] = mapped_column(
        ForeignKey("messages.id"), nullable=True, index=True
    )
    importance: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    embedding_provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(180), nullable=True)
    embedding_dimension: Mapped[int | None] = mapped_column(Integer, nullable=True)
    relevance_hint: Mapped[float | None] = mapped_column(Float, nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, default=dict, nullable=False
    )
    last_used_at: Mapped[datetime | None] = mapped_column(nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True, index=True)
    created_at: Mapped[datetime] = utc_created_column()
    updated_at: Mapped[datetime] = utc_updated_column()


class MemoryEvent(Base):
    __tablename__ = "memory_events"

    id: Mapped[str] = id_column()
    memory_id: Mapped[str] = mapped_column(ForeignKey("memories.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(40), nullable=False, default="user")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, default=dict, nullable=False
    )
    created_at: Mapped[datetime] = utc_created_column()
