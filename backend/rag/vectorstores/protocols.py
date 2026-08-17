"""Vector store protocols."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class VectorSearchResult:
    id: str
    score: float
    metadata: dict[str, Any]


@dataclass(frozen=True)
class VectorRecord:
    id: str
    vector: list[float]
    metadata: dict[str, Any]


class VectorStore(Protocol):
    store_id: str

    async def health(self) -> str: ...
    async def upsert(self, records: list[VectorRecord], *, dimension: int) -> None: ...
    async def delete(self, ids: list[str]) -> None: ...
    async def search(
        self,
        embedding: list[float],
        *,
        limit: int,
        filters: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]: ...
