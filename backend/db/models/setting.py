"""Setting persistence model."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base
from backend.db.types import id_column, utc_created_column, utc_updated_column


class Setting(Base):
    __tablename__ = "settings"

    id: Mapped[str] = id_column()
    key: Mapped[str] = mapped_column(String(180), nullable=False, unique=True, index=True)
    value: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = utc_created_column()
    updated_at: Mapped[datetime] = utc_updated_column()
