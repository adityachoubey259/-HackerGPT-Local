"""Reranker contracts and default implementation."""

from __future__ import annotations

from typing import Protocol

from backend.rag.models import RetrievalResult


class BaseReranker(Protocol):
    async def rerank(self, query: str, results: list[RetrievalResult]) -> list[RetrievalResult]: ...


class NoopReranker:
    async def rerank(self, query: str, results: list[RetrievalResult]) -> list[RetrievalResult]:
        return sorted(results, key=lambda item: item.score, reverse=True)
