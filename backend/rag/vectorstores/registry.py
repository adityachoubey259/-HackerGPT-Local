"""Vector store registry."""

from __future__ import annotations

from backend.rag.vectorstores.faiss_store import LocalFaissVectorStore
from backend.rag.vectorstores.protocols import VectorStore


class VectorStoreRegistry:
    def __init__(self, stores: list[VectorStore] | None = None) -> None:
        self._stores = {store.store_id: store for store in stores or []}
        if "faiss" not in self._stores:
            store = LocalFaissVectorStore()
            self._stores[store.store_id] = store

    def get(self, store_id: str = "faiss") -> VectorStore:
        try:
            return self._stores[store_id]
        except KeyError as exc:
            raise ValueError(f"Vector store is not configured: {store_id}") from exc
