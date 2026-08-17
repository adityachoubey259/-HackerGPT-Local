"""Path-safety validation for local ingestion."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from pathlib import Path

from backend.rag.checksums import sha256_file
from backend.rag.models import IngestionCandidate

DEFAULT_IGNORES = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".next",
    "coverage",
}

BINARY_EXTENSIONS = {
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".zip",
    ".tar",
    ".gz",
    ".7z",
    ".rar",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".mp4",
    ".mp3",
    ".sqlite",
    ".db",
}


class PathSafetyError(Exception):
    def __init__(self, message: str, *, code: str = "PATH_NOT_ALLOWED") -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class IngestionLimits:
    max_file_size_bytes: int
    allowed_extensions: frozenset[str]
    allowed_roots: tuple[Path, ...]
    ignore_patterns: tuple[str, ...] = ()


def resolve_allowed_path(candidate: Path, limits: IngestionLimits) -> Path:
    resolved = candidate.expanduser().resolve(strict=True)
    if not is_under_allowed_root(resolved, limits.allowed_roots):
        raise PathSafetyError("Path is outside configured ingestion roots.")
    return resolved


def collect_candidates(root: Path, limits: IngestionLimits) -> list[IngestionCandidate]:
    resolved = resolve_allowed_path(root, limits)
    if resolved.is_file():
        return [candidate_for_file(resolved, limits)]
    candidates: list[IngestionCandidate] = []
    for path in resolved.rglob("*"):
        if should_ignore(path, resolved, limits.ignore_patterns):
            continue
        if path.is_symlink():
            target = path.resolve(strict=True)
            if not is_under_allowed_root(target, (resolved,)):
                continue
        if path.is_file():
            try:
                candidates.append(candidate_for_file(path.resolve(strict=True), limits))
            except PathSafetyError:
                continue
    return candidates


def candidate_for_file(path: Path, limits: IngestionLimits) -> IngestionCandidate:
    if path.suffix.lower() not in limits.allowed_extensions:
        raise PathSafetyError("File extension is not allowed.", code="UNSUPPORTED_EXTENSION")
    if path.suffix.lower() in BINARY_EXTENSIONS:
        raise PathSafetyError("Binary files are not indexed.", code="BINARY_FILE")
    size = path.stat().st_size
    if size > limits.max_file_size_bytes:
        raise PathSafetyError("File exceeds ingestion size limit.", code="FILE_TOO_LARGE")
    if looks_binary(path):
        raise PathSafetyError("Binary content is not indexed.", code="BINARY_FILE")
    return IngestionCandidate(
        path=path,
        display_name=path.name,
        size_bytes=size,
        checksum=sha256_file(path),
    )


def is_under_allowed_root(path: Path, roots: tuple[Path, ...]) -> bool:
    for root in roots:
        try:
            path.relative_to(root.expanduser().resolve(strict=False))
            return True
        except ValueError:
            continue
    return False


def should_ignore(path: Path, root: Path, patterns: tuple[str, ...]) -> bool:
    parts = set(path.relative_to(root).parts)
    if parts & DEFAULT_IGNORES:
        return True
    relative = str(path.relative_to(root)).replace("\\", "/")
    return any(fnmatch.fnmatch(relative, pattern) for pattern in patterns)


def looks_binary(path: Path) -> bool:
    with path.open("rb") as handle:
        sample = handle.read(4096)
    if b"\x00" in sample:
        return True
    if not sample:
        return False
    textlike = sum(byte in b"\n\r\t\b\f" or 32 <= byte <= 126 for byte in sample)
    return textlike / len(sample) < 0.70


def sanitize_storage_name(name: str) -> str:
    base = Path(name).name
    cleaned = "".join(char if char.isalnum() or char in {"-", "_", "."} else "_" for char in base)
    cleaned = cleaned.strip("._")
    return cleaned[:160] or "document"
