"""Reusable database column helpers."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.time import utc_now


def new_uuid() -> str:
    return str(uuid.uuid4())


def id_column() -> Mapped[str]:
    return mapped_column(primary_key=True, default=new_uuid)


def utc_created_column() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


def utc_updated_column() -> Mapped[datetime]:
    return mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


JsonDict = dict[str, Any]
