"""Cybersecurity workspace service."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette import status

from backend.api.errors import ApplicationError
from backend.api.schemas.security import (
    SecurityDashboardResponse,
    SecurityExportResponse,
    SecurityFindingCreate,
    SecurityFindingListResponse,
    SecurityFindingRead,
    SecurityNoteCreate,
    SecurityNoteListResponse,
    SecurityNoteRead,
    SecurityScopeCreate,
    SecurityScopeListResponse,
    SecurityScopeRead,
    SecurityWorkspaceCreate,
    SecurityWorkspaceListResponse,
    SecurityWorkspaceRead,
    StaticReviewFinding,
    StaticReviewRequest,
    StaticReviewResponse,
    StaticSampleRequest,
    StaticSampleResponse,
    allowed_security_values,
)
from backend.core.policy import PolicyConfig
from backend.core.time import utc_now
from backend.db.models import SecurityFinding, SecurityNote, SecurityScope, SecurityWorkspace
from backend.db.repositories.sqlalchemy import (
    LOCAL_USER_ID,
    SqlAlchemySecurityRepository,
    SqlAlchemyUserRepository,
)
from backend.rag.path_safety import DEFAULT_IGNORES, is_under_allowed_root
from backend.security_workspace.models import (
    FINDING_CONFIDENCES,
    FINDING_SEVERITIES,
    SCOPE_TYPES,
    SECURITY_MODES,
)

TEXT_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".md",
    ".txt",
    ".sh",
    ".ps1",
    ".sql",
    ".html",
    ".css",
}


@dataclass(frozen=True)
class StaticRule:
    pattern: re.Pattern[str]
    title: str
    severity: str
    category: str
    remediation: str
    cwe: str | None = None


STATIC_RULES: tuple[StaticRule, ...] = (
    StaticRule(
        re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]{12,}"),
        "Possible hardcoded secret",
        "high",
        "secrets",
        "Move secrets to environment variables or a local secret store and rotate exposed values.",
        "CWE-798",
    ),
    StaticRule(
        re.compile(r"(?i)(eval|exec)\s*\("),
        "Dynamic code execution primitive",
        "medium",
        "injection",
        "Avoid dynamic execution or strictly constrain input and execution context.",
        "CWE-94",
    ),
    StaticRule(
        re.compile(r"subprocess\.[a-z_]+\([^)]*shell\s*=\s*True", re.DOTALL),
        "Shell execution with shell=True",
        "high",
        "command-execution",
        "Pass argument vectors without shell expansion and validate any user-controlled input.",
        "CWE-78",
    ),
    StaticRule(
        re.compile(r"pickle\.loads?\s*\("),
        "Unsafe pickle deserialization",
        "high",
        "deserialization",
        "Use a safe serialization format for untrusted data.",
        "CWE-502",
    ),
    StaticRule(
        re.compile(r"(?i)select\s+.+\s+from\s+.+\{.+\}"),
        "Interpolated SQL query",
        "medium",
        "sql-injection",
        "Use parameterized queries through the database driver or ORM.",
        "CWE-89",
    ),
)


class SecurityWorkspaceService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        policy: PolicyConfig,
        *,
        workspace_root: Path,
    ) -> None:
        self._session_factory = session_factory
        self._policy = policy
        self._workspace_root = workspace_root.resolve(strict=False)

    async def dashboard(self) -> SecurityDashboardResponse:
        async with self._session_factory() as session:
            repo = SqlAlchemySecurityRepository(session)
            workspaces = await repo.list_workspaces(LOCAL_USER_ID)
            scopes = await repo.list_scopes(LOCAL_USER_ID)
            _, finding_count = await repo.list_findings(LOCAL_USER_ID, limit=1, offset=0)
            values = allowed_security_values()
            return SecurityDashboardResponse(
                modes=list(values["modes"]),
                scope_types=list(values["scope_types"]),
                severity_levels=list(values["severities"]),
                confidence_levels=list(values["confidences"]),
                policy_scopes=self._policy.security.authorized_scopes,
                workspace_count=len(workspaces),
                scope_count=len(scopes),
                finding_count=finding_count,
            )

    async def list_workspaces(self) -> SecurityWorkspaceListResponse:
        async with self._session_factory() as session:
            repo = SqlAlchemySecurityRepository(session)
            workspaces = await repo.list_workspaces(LOCAL_USER_ID)
            return SecurityWorkspaceListResponse(
                items=[workspace_to_read(item) for item in workspaces]
            )

    async def create_workspace(self, body: SecurityWorkspaceCreate) -> SecurityWorkspaceRead:
        _ensure_allowed(body.mode, SECURITY_MODES, "mode")
        async with self._session_factory() as session:
            await SqlAlchemyUserRepository(session).get_or_create_local()
            repo = SqlAlchemySecurityRepository(session)
            workspace = await repo.create_workspace(
                user_id=LOCAL_USER_ID,
                name=body.name.strip(),
                mode=body.mode,
                description=body.description,
                metadata={"created_by": "user"},
            )
            await session.commit()
            return workspace_to_read(workspace)

    async def list_scopes(self, workspace_id: str | None = None) -> SecurityScopeListResponse:
        async with self._session_factory() as session:
            repo = SqlAlchemySecurityRepository(session)
            scopes = await repo.list_scopes(LOCAL_USER_ID, workspace_id=workspace_id)
            return SecurityScopeListResponse(items=[scope_to_read(item) for item in scopes])

    async def create_scope(self, body: SecurityScopeCreate) -> SecurityScopeRead:
        _ensure_allowed(body.scope_type, SCOPE_TYPES, "scope_type")
        self._validate_scope_against_policy(body.scope_type, body.target)
        async with self._session_factory() as session:
            await SqlAlchemyUserRepository(session).get_or_create_local()
            repo = SqlAlchemySecurityRepository(session)
            scope = await repo.create_scope(
                user_id=LOCAL_USER_ID,
                name=body.name.strip(),
                scope_type=body.scope_type,
                target=body.target.strip(),
                workspace_id=body.workspace_id,
                description=body.description,
                enabled=body.enabled,
                metadata={"policy_checked": True},
            )
            await session.commit()
            return scope_to_read(scope)

    async def list_findings(
        self,
        *,
        workspace_id: str | None = None,
        severity: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> SecurityFindingListResponse:
        if severity is not None:
            _ensure_allowed(severity, FINDING_SEVERITIES, "severity")
        async with self._session_factory() as session:
            repo = SqlAlchemySecurityRepository(session)
            findings, total = await repo.list_findings(
                LOCAL_USER_ID,
                workspace_id=workspace_id,
                severity=severity,
                limit=limit,
                offset=offset,
            )
            return SecurityFindingListResponse(
                items=[finding_to_read(item) for item in findings],
                total=total,
            )

    async def create_finding(self, body: SecurityFindingCreate) -> SecurityFindingRead:
        _ensure_allowed(body.severity, FINDING_SEVERITIES, "severity")
        _ensure_allowed(body.confidence, FINDING_CONFIDENCES, "confidence")
        async with self._session_factory() as session:
            await SqlAlchemyUserRepository(session).get_or_create_local()
            repo = SqlAlchemySecurityRepository(session)
            finding = await repo.create_finding(
                user_id=LOCAL_USER_ID,
                title=body.title.strip(),
                severity=body.severity,
                confidence=body.confidence,
                description=body.description,
                evidence=body.evidence,
                remediation=body.remediation,
                workspace_id=body.workspace_id,
                scope_id=body.scope_id,
                category=body.category,
                cwe=body.cwe,
                cve=body.cve,
                affected_asset=body.affected_asset,
                references=body.references,
                metadata=body.metadata,
            )
            await session.commit()
            return finding_to_read(finding)

    async def list_notes(self, workspace_id: str | None = None) -> SecurityNoteListResponse:
        async with self._session_factory() as session:
            repo = SqlAlchemySecurityRepository(session)
            notes = await repo.list_notes(LOCAL_USER_ID, workspace_id=workspace_id)
            return SecurityNoteListResponse(items=[note_to_read(item) for item in notes])

    async def create_note(self, body: SecurityNoteCreate) -> SecurityNoteRead:
        async with self._session_factory() as session:
            await SqlAlchemyUserRepository(session).get_or_create_local()
            repo = SqlAlchemySecurityRepository(session)
            note = await repo.create_note(
                user_id=LOCAL_USER_ID,
                title=body.title.strip(),
                content=body.content,
                workspace_id=body.workspace_id,
                finding_id=body.finding_id,
                tags=body.tags,
                references=body.references,
            )
            await session.commit()
            return note_to_read(note)

    async def static_review(self, body: StaticReviewRequest) -> StaticReviewResponse:
        candidates = self._collect_review_files(body.paths)
        findings: list[StaticReviewFinding] = []
        for path in candidates:
            text = path.read_text(encoding="utf-8", errors="replace")
            relative = str(path.relative_to(self._workspace_root)).replace("\\", "/")
            for rule in STATIC_RULES:
                match = rule.pattern.search(text)
                if match is None:
                    continue
                findings.append(
                    StaticReviewFinding(
                        title=rule.title,
                        severity=rule.severity,
                        confidence="medium",
                        category=rule.category,
                        affected_asset=relative,
                        evidence=_line_evidence(text, match.start()),
                        remediation=rule.remediation,
                        cwe=rule.cwe,
                    )
                )
        persisted = 0
        if body.persist_findings and findings:
            persisted = await self._persist_static_findings(body.workspace_id, findings)
        return StaticReviewResponse(
            findings=findings,
            persisted=persisted,
            scanned_files=len(candidates),
            skipped_files=0,
            diagnostics={"rules": len(STATIC_RULES), "execution": "read_only_static_analysis"},
        )

    async def inspect_sample(self, body: StaticSampleRequest) -> StaticSampleResponse:
        path = self._resolve_repo_path(body.path)
        if not path.is_file():
            raise ApplicationError(
                "SECURITY_SAMPLE_NOT_FOUND",
                "Sample path is not a file.",
                status_code=404,
            )
        content = path.read_bytes()
        strings = re.findall(rb"[\x20-\x7e]{4,}", content)
        decoded_strings = [
            item.decode("ascii", errors="replace")[:500] for item in strings[: body.max_strings]
        ]
        return StaticSampleResponse(
            path=str(path.relative_to(self._workspace_root)).replace("\\", "/"),
            size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
            strings=decoded_strings,
            diagnostics={"execution": "metadata_and_strings_only", "executed": False},
        )

    async def export_workspace(
        self, workspace_id: str, export_format: str
    ) -> SecurityExportResponse:
        async with self._session_factory() as session:
            repo = SqlAlchemySecurityRepository(session)
            workspace = await repo.get_workspace(LOCAL_USER_ID, workspace_id)
            if workspace is None:
                raise ApplicationError(
                    "SECURITY_WORKSPACE_NOT_FOUND",
                    "Workspace was not found.",
                    status_code=404,
                )
            findings, _ = await repo.list_findings(
                LOCAL_USER_ID,
                workspace_id=workspace_id,
                limit=500,
            )
            notes = await repo.list_notes(LOCAL_USER_ID, workspace_id=workspace_id)
        if export_format == "json":
            content = {
                "workspace": workspace_to_read(workspace).model_dump(mode="json"),
                "findings": [finding_to_read(item).model_dump(mode="json") for item in findings],
                "notes": [note_to_read(item).model_dump(mode="json") for item in notes],
            }
            return SecurityExportResponse(
                format="json",
                content=str(content),
                generated_at=utc_now(),
            )
        markdown = _workspace_markdown(workspace, findings, notes)
        return SecurityExportResponse(format="markdown", content=markdown, generated_at=utc_now())

    def _validate_scope_against_policy(self, scope_type: str, target: str) -> None:
        configured = self._policy.security.authorized_scopes
        if not configured:
            return
        for scope in configured:
            if scope.get("scope_type") == scope_type and str(scope.get("target")) == target:
                return
        if scope_type in {"ctf", "configured_repository"}:
            return
        raise ApplicationError(
            "SECURITY_SCOPE_NOT_AUTHORIZED",
            "Security scope is not present in policy authorized_scopes.",
            status_code=status.HTTP_403_FORBIDDEN,
            details={"scope_type": scope_type, "target": target},
        )

    def _resolve_repo_path(self, value: str) -> Path:
        path = (self._workspace_root / value).resolve(strict=True)
        if not is_under_allowed_root(path, (self._workspace_root,)):
            raise ApplicationError(
                "SECURITY_PATH_NOT_ALLOWED",
                "Path is outside the repository workspace.",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        return path

    def _collect_review_files(self, paths: Sequence[str]) -> list[Path]:
        files: list[Path] = []
        for value in paths:
            root = self._resolve_repo_path(value)
            if root.is_file() and _reviewable(root):
                files.append(root)
                continue
            for path in root.rglob("*"):
                if len(files) >= 250:
                    break
                if any(part in DEFAULT_IGNORES for part in path.parts):
                    continue
                if path.is_file() and _reviewable(path):
                    files.append(path)
        return files[:250]

    async def _persist_static_findings(
        self, workspace_id: str | None, findings: list[StaticReviewFinding]
    ) -> int:
        async with self._session_factory() as session:
            await SqlAlchemyUserRepository(session).get_or_create_local()
            repo = SqlAlchemySecurityRepository(session)
            for finding in findings:
                await repo.create_finding(
                    user_id=LOCAL_USER_ID,
                    title=finding.title,
                    severity=finding.severity,
                    confidence=finding.confidence,
                    description=finding.title,
                    evidence=finding.evidence,
                    remediation=finding.remediation,
                    workspace_id=workspace_id,
                    category=finding.category,
                    cwe=finding.cwe,
                    affected_asset=finding.affected_asset,
                    metadata={"source": "static_review"},
                )
            await session.commit()
        return len(findings)


def workspace_to_read(workspace: SecurityWorkspace) -> SecurityWorkspaceRead:
    return SecurityWorkspaceRead(
        id=workspace.id,
        name=workspace.name,
        mode=workspace.mode,
        description=workspace.description,
        active_scope_id=workspace.active_scope_id,
        enabled=workspace.enabled,
        metadata=workspace.metadata_json,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
    )


def scope_to_read(scope: SecurityScope) -> SecurityScopeRead:
    return SecurityScopeRead(
        id=scope.id,
        workspace_id=scope.workspace_id,
        name=scope.name,
        scope_type=scope.scope_type,
        target=scope.target,
        description=scope.description,
        enabled=scope.enabled,
        metadata=scope.metadata_json,
        created_at=scope.created_at,
        updated_at=scope.updated_at,
    )


def finding_to_read(finding: SecurityFinding) -> SecurityFindingRead:
    return SecurityFindingRead(
        id=finding.id,
        workspace_id=finding.workspace_id,
        scope_id=finding.scope_id,
        title=finding.title,
        severity=finding.severity,
        confidence=finding.confidence,
        category=finding.category,
        cwe=finding.cwe,
        cve=finding.cve,
        affected_asset=finding.affected_asset,
        description=finding.description,
        evidence=finding.evidence,
        remediation=finding.remediation,
        references=finding.references,
        metadata=finding.metadata_json,
        created_at=finding.created_at,
        updated_at=finding.updated_at,
    )


def note_to_read(note: SecurityNote) -> SecurityNoteRead:
    return SecurityNoteRead(
        id=note.id,
        workspace_id=note.workspace_id,
        finding_id=note.finding_id,
        title=note.title,
        content=note.content,
        tags=note.tags,
        references=note.references,
        metadata=note.metadata_json,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


def _ensure_allowed(value: str, allowed: tuple[str, ...], field: str) -> None:
    if value not in allowed:
        raise ApplicationError(
            "SECURITY_INVALID_VALUE",
            f"Unsupported {field}.",
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            details={"allowed": list(allowed)},
        )


def _reviewable(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTENSIONS and path.stat().st_size <= 512_000


def _line_evidence(text: str, offset: int) -> str:
    line_no = text[:offset].count("\n") + 1
    line = text.splitlines()[line_no - 1].strip()
    return f"line {line_no}: {line[:300]}"


def _workspace_markdown(
    workspace: SecurityWorkspace,
    findings: list[SecurityFinding],
    notes: list[SecurityNote],
) -> str:
    lines = [
        f"# {workspace.name}",
        "",
        f"Mode: `{workspace.mode}`",
        "",
        workspace.description,
        "",
        "## Findings",
    ]
    for finding in findings:
        lines.extend(
            [
                "",
                f"### {finding.title}",
                "",
                f"- Severity: `{finding.severity}`",
                f"- Confidence: `{finding.confidence}`",
                f"- Asset: `{finding.affected_asset or 'n/a'}`",
                "",
                finding.description,
                "",
                "Evidence:",
                "",
                f"```text\n{finding.evidence}\n```",
                "",
                f"Remediation: {finding.remediation}",
            ]
        )
    lines.extend(["", "## Notes"])
    for note in notes:
        lines.extend(["", f"### {note.title}", "", note.content])
    return "\n".join(lines).strip() + "\n"
