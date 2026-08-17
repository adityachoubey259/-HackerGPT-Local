"""Security validation helpers."""

from __future__ import annotations

from pathlib import Path

from backend.security.types import UNTRUSTED_BOUNDARIES, ExecutionPermission, TrustBoundary


class SecurityValidationError(ValueError):
    """Raised when a security validation fails."""


def is_untrusted(boundary: TrustBoundary) -> bool:
    return boundary in UNTRUSTED_BOUNDARIES


def ensure_trusted_instruction_source(boundary: TrustBoundary) -> None:
    if is_untrusted(boundary):
        msg = f"{boundary.value} is data, not trusted application instructions"
        raise SecurityValidationError(msg)


def require_permission(
    requested: ExecutionPermission,
    maximum: ExecutionPermission,
) -> None:
    ordering = {
        ExecutionPermission.READ_ONLY: 0,
        ExecutionPermission.WRITE_LOCAL: 1,
        ExecutionPermission.HIGH_IMPACT: 2,
    }
    if ordering[requested] > ordering[maximum]:
        msg = f"{requested.value} exceeds allowed permission {maximum.value}"
        raise SecurityValidationError(msg)


def resolve_workspace_path(workspace_root: Path, requested_path: Path) -> Path:
    root = workspace_root.resolve()
    candidate = requested_path
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    if resolved != root and root not in resolved.parents:
        msg = f"path escapes workspace: {requested_path}"
        raise SecurityValidationError(msg)
    return resolved
