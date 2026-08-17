"""Tool execution audit and confirmation models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base
from backend.db.types import id_column, utc_created_column, utc_updated_column


class ToolExecution(Base):
    __tablename__ = "tool_executions"

    id: Mapped[str] = id_column()
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    conversation_id: Mapped[str | None] = mapped_column(
        ForeignKey("conversations.id"), nullable=True, index=True
    )
    message_id: Mapped[str | None] = mapped_column(ForeignKey("messages.id"), nullable=True)
    agent_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    request_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    generation_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    tool_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    permission_class: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    input: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    working_directory: Mapped[str | None] = mapped_column(Text, nullable=True)
    command_display: Mapped[str | None] = mapped_column(Text, nullable=True)
    stdout: Mapped[str | None] = mapped_column(Text, nullable=True)
    stderr: Mapped[str | None] = mapped_column(Text, nullable=True)
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    truncated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = utc_created_column()
    updated_at: Mapped[datetime] = utc_updated_column()


class ToolConfirmation(Base):
    __tablename__ = "tool_confirmations"

    id: Mapped[str] = id_column()
    execution_id: Mapped[str] = mapped_column(
        ForeignKey("tool_executions.id"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    tool_name: Mapped[str] = mapped_column(String(120), nullable=False)
    permission_class: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    risk_summary: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False, index=True)
    decided_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = utc_created_column()
    updated_at: Mapped[datetime] = utc_updated_column()
