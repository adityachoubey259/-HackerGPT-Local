"""Embedding provider registry."""

from __future__ import annotations

from backend.rag.embeddings.base import BaseEmbeddingProvider, EmbeddingProviderError
from backend.rag.embeddings.local import LocalHashEmbeddingProvider


class EmbeddingProviderRegistry:
    def __init__(self, providers: list[BaseEmbeddingProvider] | None = None) -> None:
        self._providers = {provider.provider_id: provider for provider in providers or []}
        if "local" not in self._providers:
            local = LocalHashEmbeddingProvider()
            self._providers[local.provider_id] = local

    def get(self, provider_id: str = "local") -> BaseEmbeddingProvider:
        provider = self._providers.get(provider_id)
        if provider is None:
            raise EmbeddingProviderError(
                f"Embedding provider is not configured: {provider_id}",
                code="EMBEDDING_PROVIDER_UNAVAILABLE",
            )
        return provider

    def providers(self) -> list[BaseEmbeddingProvider]:
        return list(self._providers.values())
