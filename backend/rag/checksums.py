"""Stable checksum helpers for documents, chunks, and embeddings."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def cache_key_checksum(
    content_checksum: str, provider: str, model: str, config: dict[str, Any]
) -> str:
    payload = {
        "content_checksum": content_checksum,
        "provider": provider,
        "model": model,
        "config": config,
    }
    return sha256_text(json.dumps(payload, sort_keys=True, separators=(",", ":")))
