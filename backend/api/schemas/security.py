"""Cybersecurity workspace API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from backend.security_workspace.models import (
    FINDING_CONFIDENCES,
    FINDING_SEVERITIES,
    SCOPE_TYPES,
    SECURITY_MODES,
)


class SecurityWorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    mode: str = Field(default="general-security")
    description: str = Field(default="", max_length=4000)


class SecurityScopeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    scope_type: str
    target: str = Field(min_length=1, max_length=500)
    workspace_id: str | None = None
    description: str = Field(default="", max_length=4000)
    enabled: bool = True


class SecurityFindingCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    severity: str = Field(default="medium")
    confidence: str = Field(default="medium")
    description: str = Field(default="", max_length=12000)
    evidence: str = Field(default="", max_length=12000)
    remediation: str = Field(default="", max_length=12000)
    workspace_id: str | None = None
    scope_id: str | None = None
    category: str | None = Field(default=None, max_length=120)
    cwe: str | None = Field(default=None, max_length=40)
    cve: str | None = Field(default=None, max_length=40)
    affected_asset: str | None = Field(default=None, max_length=500)
    references: list[str] = Field(default_factory=list, max_length=30)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SecurityNoteCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    content: str = Field(default="", max_length=50000)
    workspace_id: str | None = None
    finding_id: str | None = None
    tags: list[str] = Field(default_factory=list, max_length=30)
    references: list[str] = Field(default_factory=list, max_length=30)


class StaticReviewRequest(BaseModel):
    paths: list[str] = Field(default_factory=lambda: ["."], max_length=20)
    workspace_id: str | None = None
    persist_findings: bool = False


class StaticSampleRequest(BaseModel):
    path: str = Field(min_length=1, max_length=1000)
    max_strings: int = Field(default=80, ge=1, le=500)


class SecurityWorkspaceRead(BaseModel):
    id: str
    name: str
    mode: str
    description: str
    active_scope_id: str | None
    enabled: bool
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class SecurityScopeRead(BaseModel):
    id: str
    workspace_id: str | None
    name: str
    scope_type: str
    target: str
    description: str
    enabled: bool
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class SecurityFindingRead(BaseModel):
    id: str
    workspace_id: str | None
    scope_id: str | None
    title: str
    severity: str
    confidence: str
    category: str | None
    cwe: str | None
    cve: str | None
    affected_asset: str | None
    description: str
    evidence: str
    remediation: str
    references: list[str]
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class SecurityNoteRead(BaseModel):
    id: str
    workspace_id: str | None
    finding_id: str | None
    title: str
    content: str
    tags: list[str]
    references: list[str]
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class SecurityDashboardResponse(BaseModel):
    modes: list[str]
    scope_types: list[str]
    severity_levels: list[str]
    confidence_levels: list[str]
    policy_scopes: list[dict[str, Any]]
    workspace_count: int
    scope_count: int
    finding_count: int


class SecurityWorkspaceListResponse(BaseModel):
    items: list[SecurityWorkspaceRead]


class SecurityScopeListResponse(BaseModel):
    items: list[SecurityScopeRead]


class SecurityFindingListResponse(BaseModel):
    items: list[SecurityFindingRead]
    total: int


class SecurityNoteListResponse(BaseModel):
    items: list[SecurityNoteRead]


class StaticReviewFinding(BaseModel):
    title: str
    severity: str
    confidence: str
    category: str
    affected_asset: str
    evidence: str
    remediation: str
    cwe: str | None = None


class StaticReviewResponse(BaseModel):
    findings: list[StaticReviewFinding]
    persisted: int
    scanned_files: int
    skipped_files: int
    diagnostics: dict[str, Any]


class StaticSampleResponse(BaseModel):
    path: str
    size_bytes: int
    sha256: str
    strings: list[str]
    diagnostics: dict[str, Any]


class SecurityExportResponse(BaseModel):
    format: str
    content: str
    generated_at: datetime


def allowed_security_values() -> dict[str, tuple[str, ...]]:
    return {
        "modes": SECURITY_MODES,
        "scope_types": SCOPE_TYPES,
        "severities": FINDING_SEVERITIES,
        "confidences": FINDING_CONFIDENCES,
    }
