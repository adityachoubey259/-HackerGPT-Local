"""Message persistence model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base
from backend.db.types import id_column, utc_created_column, utc_updated_column

if TYPE_CHECKING:
    from backend.db.models.conversation import Conversation


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = id_column()
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    client_request_id: Mapped[str | None] = mapped_column(String(120), nullable=True, unique=True)
    generation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    generation_status: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    model: Mapped[str | None] = mapped_column(String(240), nullable=True)
    finish_reason: Mapped[str | None] = mapped_column(String(80), nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    time_to_first_token_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    tokens_per_second: Mapped[float | None] = mapped_column(Float, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, default=dict, nullable=False
    )
    created_at: Mapped[datetime] = utc_created_column()
    updated_at: Mapped[datetime] = utc_updated_column()

    conversation: Mapped[Conversation] = relationship("Conversation", back_populates="messages")
