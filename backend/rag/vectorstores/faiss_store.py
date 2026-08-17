"""Persisted local FAISS-style vector store."""

from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path
from typing import Any

from backend.rag.vectorstores.protocols import VectorRecord, VectorSearchResult


class DimensionMismatchError(Exception):
    pass


class LocalFaissVectorStore:
    store_id = "faiss"

    def __init__(self, path: Path = Path("data/vectorstores/faiss_index.json")) -> None:
        self._path = path
        self._records: dict[str, VectorRecord] = {}
        self._dimension: int | None = None
        self._loaded = False

    async def health(self) -> str:
        try:
            self._load()
        except Exception:
            return "needs_rebuild"
        return "ok"

    async def upsert(self, records: list[VectorRecord], *, dimension: int) -> None:
        self._load()
        if self._dimension is not None and self._dimension != dimension:
            raise DimensionMismatchError("Vector dimension does not match existing index.")
        self._dimension = dimension
        for record in records:
            if len(record.vector) != dimension:
                raise DimensionMismatchError("Vector dimension does not match record vector.")
            self._records[record.id] = record
        self._persist()

    async def delete(self, ids: list[str]) -> None:
        self._load()
        for record_id in ids:
            self._records.pop(record_id, None)
        self._persist()

    async def search(
        self,
        embedding: list[float],
        *,
        limit: int,
        filters: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        self._load()
        if self._dimension is not None and len(embedding) != self._dimension:
            raise DimensionMismatchError("Query vector dimension does not match index.")
        scored = [
            VectorSearchResult(
                id=record.id,
                score=cosine_similarity(embedding, record.vector),
                metadata=record.metadata,
            )
            for record in self._records.values()
            if matches_filters(record.metadata, filters or {})
        ]
        return sorted(scored, key=lambda item: item.score, reverse=True)[:limit]

    def _load(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        if not self._path.exists():
            return
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        self._dimension = payload.get("dimension")
        self._records = {
            str(record["id"]): VectorRecord(
                id=str(record["id"]),
                vector=[float(value) for value in record["vector"]],
                metadata=dict(record.get("metadata", {})),
            )
            for record in payload.get("records", [])
        }

    def _persist(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "dimension": self._dimension,
            "records": [
                {"id": record.id, "vector": record.vector, "metadata": record.metadata}
                for record in self._records.values()
            ],
        }
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=self._path.parent,
            delete=False,
        ) as handle:
            json.dump(payload, handle, separators=(",", ":"))
            temp_path = Path(handle.name)
        temp_path.replace(self._path)


def cosine_similarity(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right, strict=False))
    left_norm = math.sqrt(sum(value * value for value in left)) or 1.0
    right_norm = math.sqrt(sum(value * value for value in right)) or 1.0
    return round(dot / (left_norm * right_norm), 8)


def matches_filters(metadata: dict[str, Any], filters: dict[str, Any]) -> bool:
    for key, expected in filters.items():
        if expected is None:
            continue
        actual = metadata.get(key)
        if isinstance(expected, list):
            if actual not in expected:
                return False
        elif actual != expected:
            return False
    return True
