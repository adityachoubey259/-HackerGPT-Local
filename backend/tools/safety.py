"""Safety helpers for tool execution."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from backend.core.policy import PolicyConfig

SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*([^\s'\";]+)"),
    re.compile(r"(?i)(bearer)\s+([A-Za-z0-9._\-]+)"),
]


class ToolSafetyError(ValueError):
    def __init__(self, message: str, *, code: str = "TOOL_SAFETY_ERROR") -> None:
        super().__init__(message)
        self.code = code


def stable_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def redact_secrets(text: str) -> str:
    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub(lambda match: f"{match.group(1)}=[REDACTED]", redacted)
    return redacted


def truncate_text(text: str, limit_bytes: int) -> tuple[str, bool]:
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) <= limit_bytes:
        return text, False
    truncated = encoded[:limit_bytes].decode("utf-8", errors="ignore")
    return f"{truncated}\n[output truncated]", True


def resolve_tool_path(workspace_root: Path, policy: PolicyConfig, raw_path: str | None) -> Path:
    candidate = Path(raw_path or ".")
    root = workspace_root.resolve(strict=False)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve(strict=False)
    allowed_roots = [
        (root / configured).resolve(strict=False)
        if not Path(configured).is_absolute()
        else Path(configured).resolve(strict=False)
        for configured in policy.command_execution.allowed_tool_roots
    ]
    for allowed in allowed_roots:
        try:
            resolved.relative_to(allowed)
            return resolved
        except ValueError:
            continue
    raise ToolSafetyError("Path is outside configured tool roots.", code="PATH_NOT_ALLOWED")


def display_argv(argv: list[str]) -> str:
    return " ".join(quote_arg(part) for part in argv)


def quote_arg(value: str) -> str:
    if not value:
        return '""'
    if re.search(r"\s|[;&|<>$`\"']", value):
        return json.dumps(value)
    return value
