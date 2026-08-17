"""Training artifact filesystem helpers."""

from __future__ import annotations

import hashlib
from pathlib import Path


def file_checksums(path: Path) -> dict[str, str]:
    checksums: dict[str, str] = {}
    if not path.exists():
        return checksums
    for item in sorted(path.rglob("*")):
        if item.is_file():
            checksums[str(item.relative_to(path)).replace("\\", "/")] = sha256_file(item)
    return checksums


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
