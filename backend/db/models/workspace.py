"""Workspace, CodingTask, and WorkspaceChange ORM models."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    root_path: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    trusted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    git_repository: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    git_branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language_summary: Mapped[str | None] = mapped_column(String(255), nullable=True)
    framework_summary: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    last_opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    tasks: Mapped[list[CodingTask]] = relationship(
        "CodingTask", back_populates="workspace", cascade="all, delete-orphan"
    )


class CodingTask(Base):
    __tablename__ = "coding_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_request: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(String(50), nullable=False, default="queued")
    mode: Mapped[str] = mapped_column(String(50), nullable=False, default="agent")
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    files_read: Mapped[dict[str, Any]] = mapped_column(JSON, default=list, nullable=False)
    files_modified: Mapped[dict[str, Any]] = mapped_column(JSON, default=list, nullable=False)
    commands_run: Mapped[dict[str, Any]] = mapped_column(JSON, default=list, nullable=False)
    tests_run: Mapped[dict[str, Any]] = mapped_column(JSON, default=list, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    workspace: Mapped[Workspace] = relationship("Workspace", back_populates="tasks")
    changes: Mapped[list[WorkspaceChange]] = relationship(
        "WorkspaceChange", back_populates="task", cascade="all, delete-orphan"
    )


class WorkspaceChange(Base):
    __tablename__ = "workspace_changes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("coding_tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    old_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    new_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    patch_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    old_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    task: Mapped[CodingTask] = relationship("CodingTask", back_populates="changes")
