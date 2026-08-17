"""Agent persistence models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base
from backend.db.types import id_column, utc_created_column, utc_updated_column


class CustomAgent(Base):
    __tablename__ = "custom_agents"

    id: Mapped[str] = id_column()
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    built_in_origin: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = utc_created_column()
    updated_at: Mapped[datetime] = utc_updated_column()
