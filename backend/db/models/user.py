"""User persistence model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base
from backend.db.types import id_column, utc_created_column, utc_updated_column

if TYPE_CHECKING:
    from backend.db.models.conversation import Conversation


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = id_column()
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    username: Mapped[str | None] = mapped_column(String(80), nullable=True, unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(300), nullable=True)
    role: Mapped[str] = mapped_column(String(40), default="user", nullable=False)
    is_bootstrap: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auth_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = utc_created_column()
    updated_at: Mapped[datetime] = utc_updated_column()

    conversations: Mapped[list[Conversation]] = relationship(
        "Conversation",
        back_populates="user",
        cascade="all, delete-orphan",
    )
