"""Conversation persistence model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base
from backend.db.types import id_column, utc_created_column, utc_updated_column

if TYPE_CHECKING:
    from backend.db.models.message import Message
    from backend.db.models.user import User


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = id_column()
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    agent_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = utc_created_column()
    updated_at: Mapped[datetime] = utc_updated_column()

    user: Mapped[User] = relationship("User", back_populates="conversations")
    messages: Mapped[list[Message]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )
