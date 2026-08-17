"""Qdrant vector-store adapter."""

from __future__ import annotations

from typing import Any

import httpx

from backend.rag.vectorstores.protocols import VectorRecord, VectorSearchResult


class QdrantVectorStore:
    store_id = "qdrant"

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:6333",
        collection: str = "hackergpt_knowledge",
        *,
        timeout: float = 10.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._collection = collection
        self._timeout = timeout

    async def health(self) -> str:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(f"{self._base_url}/readyz")
            return "ok" if response.status_code < 400 else "unavailable"
        except httpx.HTTPError:
            return "unavailable"

    async def upsert(self, records: list[VectorRecord], *, dimension: int) -> None:
        points = [
            {"id": record.id, "vector": record.vector, "payload": record.metadata}
            for record in records
        ]
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            await client.put(
                f"{self._base_url}/collections/{self._collection}",
                json={"vectors": {"size": dimension, "distance": "Cosine"}},
            )
            response = await client.put(
                f"{self._base_url}/collections/{self._collection}/points",
                json={"points": points},
            )
        response.raise_for_status()

    async def delete(self, ids: list[str]) -> None:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/collections/{self._collection}/points/delete",
                json={"points": ids},
            )
        response.raise_for_status()

    async def search(
        self,
        embedding: list[float],
        *,
        limit: int,
        filters: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        body: dict[str, Any] = {"vector": embedding, "limit": limit, "with_payload": True}
        if filters:
            body["filter"] = {
                "must": [
                    {"key": key, "match": {"value": value}}
                    for key, value in filters.items()
                    if value is not None
                ]
            }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/collections/{self._collection}/points/search",
                json=body,
            )
        response.raise_for_status()
        return [
            VectorSearchResult(
                id=str(item["id"]),
                score=float(item.get("score", 0.0)),
                metadata=dict(item.get("payload", {})),
            )
            for item in response.json().get("result", [])
        ]
