"""Workspace management, file operations, patch application, and task execution engine."""

from __future__ import annotations

import difflib
import hashlib
import re
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class WorkspaceConflictError(Exception):
    """Raised when a file has been modified since it was read."""

    def __init__(self, message: str, current_hash: str | None = None) -> None:
        super().__init__(message)
        self.current_hash = current_hash


class PathOutsideWorkspaceError(Exception):
    """Raised when a path escapes the canonical workspace boundary."""


class FileNode(BaseModel):
    name: str
    path: str
    is_directory: bool
    size: int = 0
    children: list[FileNode] | None = None


def canonicalize_and_validate_path(workspace_root: Path | str, relative_or_abs: Path | str) -> Path:
    """Validate that target path is strictly within canonical workspace root boundary.

    Prevents ../ escape, symlink escape, UNC, and case tricks.
    """
    root = Path(workspace_root).resolve(strict=False)
    target = Path(relative_or_abs)

    if not target.is_absolute():
        target = root / target

    resolved_target = target.resolve(strict=False)

    try:
        resolved_target.relative_to(root)
    except ValueError as exc:
        raise PathOutsideWorkspaceError(
            f"Path '{target}' is outside canonical workspace boundary '{root}'"
        ) from exc

    return resolved_target


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of a file's raw bytes."""
    if not file_path.is_file():
        return ""
    hasher = hashlib.sha256()
    with file_path.open("rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def is_binary_file(file_path: Path) -> bool:
    """Check if file is binary by inspecting first 8KB."""
    if not file_path.is_file():
        return False
    try:
        with file_path.open("rb") as f:
            chunk = f.read(8192)
            if b"\x00" in chunk:
                return True
            # High proportion of non-printable bytes
            text_characters = bytearray(
                {7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)) - {0x7F}
            )
            non_text = chunk.translate(None, text_characters)
            return len(non_text) / (len(chunk) or 1) > 0.3
    except OSError:
        return True


IGNORED_DIRECTORIES = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
}


def generate_directory_tree(
    root_path: Path, current_path: Path | None = None, max_depth: int = 4
) -> FileNode:
    root = root_path.resolve()
    curr = (current_path or root).resolve()
    rel = str(curr.relative_to(root)) if curr != root else "."

    if max_depth < 0:
        return FileNode(name=curr.name or rel, path=rel, is_directory=curr.is_dir())

    children: list[FileNode] = []
    if curr.is_dir():
        try:
            for item in sorted(curr.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                if item.name in IGNORED_DIRECTORIES or item.name.startswith("."):
                    if item.name not in {".env", ".gitignore", "AGENTS.md"}:
                        continue
                if item.is_dir():
                    children.append(generate_directory_tree(root, item, max_depth=max_depth - 1))
                else:
                    item_rel = str(item.relative_to(root))
                    children.append(
                        FileNode(
                            name=item.name,
                            path=item_rel,
                            is_directory=False,
                            size=item.stat().st_size,
                        )
                    )
        except OSError:
            pass

    return FileNode(
        name=curr.name or rel,
        path=rel,
        is_directory=curr.is_dir(),
        children=children if curr.is_dir() else None,
    )


def search_workspace_text(
    workspace_root: Path, query: str, is_regex: bool = False, max_results: int = 50
) -> list[dict[str, Any]]:
    root = workspace_root.resolve()
    results: list[dict[str, Any]] = []

    # Try ripgrep if installed on host
    rg = shutil.which("rg")
    if rg:
        cmd = [
            rg,
            "--line-number",
            "--column",
            "--no-heading",
            "--max-count",
            "10",
            "--max-filesize",
            "1M",
        ]
        if not is_regex:
            cmd.append("-F")
        cmd.extend(["-e", query, str(root)])
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5, check=False)  # noqa: S603
            for line in proc.stdout.splitlines():
                parts = line.split(":", 3)
                if len(parts) >= 4:
                    fpath, lineno, col, content = parts[0], parts[1], parts[2], parts[3]
                    try:
                        rel_path = str(Path(fpath).relative_to(root))
                        results.append(
                            {
                                "file": rel_path,
                                "line": int(lineno),
                                "column": int(col),
                                "text": content.strip()[:200],
                            }
                        )
                    except ValueError:
                        continue
                if len(results) >= max_results:
                    break
            if results:
                return results
        except Exception:  # noqa: S110
            pass

    # Fallback Python text search
    pattern = re.compile(query if is_regex else re.escape(query))
    for item_path in root.rglob("*"):
        if item_path.is_file() and not is_binary_file(item_path):
            if any(part in IGNORED_DIRECTORIES for part in item_path.parts):
                continue
            try:
                rel_path = str(item_path.relative_to(root))
                with item_path.open("r", encoding="utf-8", errors="ignore") as f:
                    for i, line in enumerate(f, 1):
                        if pattern.search(line):
                            results.append(
                                {
                                    "file": rel_path,
                                    "line": i,
                                    "column": 1,
                                    "text": line.strip()[:200],
                                }
                            )
                            if len(results) >= max_results:
                                return results
            except OSError:
                continue

    return results


def apply_patch_to_file(
    file_path: Path, patch_text: str, expected_hash: str | None = None
) -> tuple[str, str]:
    """Apply a context diff / replace patch atomically.

    Returns: (new_hash, unified_diff)
    """
    if expected_hash and file_path.is_file():
        current_hash = compute_file_hash(file_path)
        if current_hash != expected_hash:
            msg = (
                f"File '{file_path.name}' was modified externally "
                f"(expected {expected_hash[:8]}, got {current_hash[:8]})"
            )
            raise WorkspaceConflictError(msg, current_hash=current_hash)

    old_content = (
        file_path.read_text(encoding="utf-8", errors="ignore") if file_path.is_file() else ""
    )

    # Parse SEARCH/REPLACE block or exact replacements
    new_content = patch_text
    if "<<<<<<< SEARCH" in patch_text and "=======" in patch_text:
        parts = patch_text.split("<<<<<<< SEARCH\n")
        curr = old_content
        for part in parts[1:]:
            if "=======\n" not in part or ">>>>>>> REPLACE" not in part:
                continue
            search_block, rest = part.split("=======\n", 1)
            replace_block, _ = rest.split(">>>>>>> REPLACE", 1)
            if search_block in curr:
                curr = curr.replace(search_block, replace_block, 1)
        new_content = curr

    # Atomic write
    tmp_path = file_path.parent / f".tmp_{uuid.uuid4().hex}_{file_path.name}"
    tmp_path.write_text(new_content, encoding="utf-8")
    tmp_path.replace(file_path)

    new_hash = compute_file_hash(file_path)
    diff = "".join(
        difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{file_path.name}",
            tofile=f"b/{file_path.name}",
        )
    )

    return new_hash, diff
