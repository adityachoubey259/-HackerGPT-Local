from __future__ import annotations

from pathlib import Path

import pytest

from backend.security.types import ExecutionPermission, TrustBoundary
from backend.security.validation import (
    SecurityValidationError,
    ensure_trusted_instruction_source,
    require_permission,
    resolve_workspace_path,
)


def test_untrusted_content_cannot_be_instruction_source() -> None:
    with pytest.raises(SecurityValidationError, match="data, not trusted"):
        ensure_trusted_instruction_source(TrustBoundary.RETRIEVED_CONTENT)


def test_permission_ordering_rejects_higher_permission() -> None:
    with pytest.raises(SecurityValidationError, match="exceeds"):
        require_permission(ExecutionPermission.HIGH_IMPACT, ExecutionPermission.READ_ONLY)


def test_workspace_path_helper_allows_inside_path(tmp_path: Path) -> None:
    resolved = resolve_workspace_path(tmp_path, Path("docs/file.txt"))
    assert tmp_path.resolve() in resolved.parents


def test_workspace_path_helper_rejects_escape(tmp_path: Path) -> None:
    with pytest.raises(SecurityValidationError, match="escapes workspace"):
        resolve_workspace_path(tmp_path, Path("../outside.txt"))
