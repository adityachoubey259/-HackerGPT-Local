"""Embedding provider contracts."""

from __future__ import annotations

from typing import Protocol

from backend.rag.models import EmbeddedText


class EmbeddingProviderError(Exception):
    def __init__(self, message: str, *, code: str = "EMBEDDING_FAILED") -> None:
        super().__init__(message)
        self.code = code


class BaseEmbeddingProvider(Protocol):
    provider_id: str
    model_id: str
    dimension: int
    local: bool

    async def embed_texts(self, texts: list[str]) -> list[EmbeddedText]: ...
