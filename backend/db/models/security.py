"""Cybersecurity workspace models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base
from backend.db.types import id_column, utc_created_column, utc_updated_column


class SecurityWorkspace(Base):
    __tablename__ = "security_workspaces"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_security_workspaces_user_name"),)

    id: Mapped[str] = id_column()
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    mode: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    active_scope_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = utc_created_column()
    updated_at: Mapped[datetime] = utc_updated_column()


class SecurityScope(Base):
    __tablename__ = "security_scopes"
    __table_args__ = (
        UniqueConstraint("user_id", "workspace_id", "name", name="uq_security_scopes_name"),
    )

    id: Mapped[str] = id_column()
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    workspace_id: Mapped[str | None] = mapped_column(
        ForeignKey("security_workspaces.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    target: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = utc_created_column()
    updated_at: Mapped[datetime] = utc_updated_column()


class SecurityFinding(Base):
    __tablename__ = "security_findings"

    id: Mapped[str] = id_column()
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    workspace_id: Mapped[str | None] = mapped_column(
        ForeignKey("security_workspaces.id"), nullable=True, index=True
    )
    scope_id: Mapped[str | None] = mapped_column(
        ForeignKey("security_scopes.id"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    confidence: Mapped[str] = mapped_column(String(32), default="medium", nullable=False)
    category: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    cwe: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    cve: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    affected_asset: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    evidence: Mapped[str] = mapped_column(Text, default="", nullable=False)
    remediation: Mapped[str] = mapped_column(Text, default="", nullable=False)
    references: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = utc_created_column()
    updated_at: Mapped[datetime] = utc_updated_column()


class SecurityNote(Base):
    __tablename__ = "security_notes"

    id: Mapped[str] = id_column()
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    workspace_id: Mapped[str | None] = mapped_column(
        ForeignKey("security_workspaces.id"), nullable=True, index=True
    )
    finding_id: Mapped[str | None] = mapped_column(
        ForeignKey("security_findings.id"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    references: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = utc_created_column()
    updated_at: Mapped[datetime] = utc_updated_column()
