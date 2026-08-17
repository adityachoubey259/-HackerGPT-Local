"""Retrieval orchestration."""

from __future__ import annotations

import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.core.logging import get_logger
from backend.db.models import Document, DocumentChunk
from backend.db.repositories.sqlalchemy import SqlAlchemyDocumentRepository
from backend.rag.embeddings.registry import EmbeddingProviderRegistry
from backend.rag.models import Citation, RagContextPack, RetrievalFilter, RetrievalResult
from backend.rag.rerankers import BaseReranker, NoopReranker
from backend.rag.text import estimate_tokens
from backend.rag.vectorstores.protocols import VectorSearchResult
from backend.rag.vectorstores.registry import VectorStoreRegistry

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class RetrievalConfig:
    max_chunks: int = 5
    min_relevance: float = 0.05
    per_document_limit: int = 3
    context_token_budget: int = 900


class RetrievalService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        embeddings: EmbeddingProviderRegistry,
        vector_stores: VectorStoreRegistry,
        *,
        reranker: BaseReranker | None = None,
        config: RetrievalConfig | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._embeddings = embeddings
        self._vector_stores = vector_stores
        self._reranker = reranker or NoopReranker()
        self._config = config or RetrievalConfig()

    async def retrieve(
        self,
        user_id: str,
        query: str,
        *,
        filters: RetrievalFilter | None = None,
    ) -> RagContextPack:
        started = time.perf_counter()
        provider = self._embeddings.get("local")
        embedded = (await provider.embed_texts([query]))[0]
        store = self._vector_stores.get("faiss")
        search_filters: dict[str, object] = {"user_id": user_id}
        if filters and filters.document_ids:
            search_filters["document_id"] = filters.document_ids
        vector_hits = await store.search(
            embedded.vector, limit=self._config.max_chunks * 4, filters=search_filters
        )
        async with self._session_factory() as session:
            repo = SqlAlchemyDocumentRepository(session)
            chunks = await repo.get_chunks_by_ids([hit.id for hit in vector_hits])
            documents = await repo.get_documents_by_ids([chunk.document_id for chunk in chunks])
        chunk_by_id = {chunk.id: chunk for chunk in chunks}
        document_by_id = {document.id: document for document in documents}
        results = self._score_results(query, vector_hits, chunk_by_id, document_by_id)
        results = [item for item in results if item.score >= self._config.min_relevance]
        results = await self._reranker.rerank(query, results)
        selected = select_diverse(results, self._config.max_chunks, self._config.per_document_limit)
        packed = pack_context(selected, self._config.context_token_budget)
        duration_ms = round((time.perf_counter() - started) * 1000, 3)
        logger.info(
            "rag.retrieve",
            candidate_count=len(vector_hits),
            selected_chunks=len(packed.results),
            duration_ms=duration_ms,
            source_count=len({result.document_id for result in packed.results}),
        )
        return packed.model_copy(
            update={
                "diagnostics": packed.diagnostics
                | {
                    "retrieval_ms": duration_ms,
                    "candidate_count": len(vector_hits),
                    "embedding_provider": provider.provider_id,
                    "embedding_model": provider.model_id,
                }
            }
        )

    def _score_results(
        self,
        query: str,
        vector_hits: list[VectorSearchResult],
        chunk_by_id: dict[str, DocumentChunk],
        document_by_id: dict[str, Document],
    ) -> list[RetrievalResult]:
        results: list[RetrievalResult] = []
        for hit in vector_hits:
            chunk = chunk_by_id.get(hit.id)
            if chunk is None:
                continue
            document = document_by_id.get(chunk.document_id)
            if document is None:
                continue
            lexical = lexical_score(query, chunk.text)
            score = round((hit.score * 0.78) + (lexical * 0.22), 8)
            results.append(
                RetrievalResult(
                    chunk_id=chunk.id,
                    document_id=document.id,
                    citation_id=chunk.citation_id,
                    text=chunk.text,
                    score=score,
                    lexical_score=lexical,
                    vector_score=hit.score,
                    file_name=document.name,
                    source_path=chunk.source_path,
                    page_number=chunk.page_number,
                    section=chunk.section,
                    metadata=chunk.metadata_json,
                )
            )
        return results


def lexical_score(query: str, text: str) -> float:
    query_terms = Counter(tokens(query))
    if not query_terms:
        return 0.0
    text_terms = Counter(tokens(text))
    overlap = sum(min(count, text_terms.get(term, 0)) for term, count in query_terms.items())
    return round(overlap / sum(query_terms.values()), 8)


def tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_]{2,}", text.lower())


def select_diverse(
    results: list[RetrievalResult],
    limit: int,
    per_document_limit: int,
) -> list[RetrievalResult]:
    selected: list[RetrievalResult] = []
    per_document: dict[str, int] = defaultdict(int)
    seen_text: set[str] = set()
    for result in results:
        text_key = result.text[:300]
        if text_key in seen_text or per_document[result.document_id] >= per_document_limit:
            continue
        selected.append(result)
        seen_text.add(text_key)
        per_document[result.document_id] += 1
        if len(selected) >= limit:
            break
    return selected


def pack_context(results: list[RetrievalResult], token_budget: int) -> RagContextPack:
    citations: list[Citation] = []
    blocks: list[str] = []
    used = 0
    selected: list[RetrievalResult] = []
    for index, result in enumerate(results, start=1):
        citation_id = f"[K{index}]"
        block = f"{citation_id} {result.file_name}"
        if result.page_number is not None:
            block += f" page {result.page_number}"
        if result.section:
            block += f" section {result.section}"
        block += f"\n{result.text}"
        cost = estimate_tokens(block)
        if used + cost > token_budget:
            continue
        used += cost
        selected.append(result.model_copy(update={"citation_id": citation_id}))
        citations.append(
            Citation(
                citation_id=citation_id,
                chunk_id=result.chunk_id,
                document_id=result.document_id,
                file_name=result.file_name,
                source_path=result.source_path,
                page_number=result.page_number,
                section=result.section,
                score=result.score,
            )
        )
        blocks.append(block)
    return RagContextPack(
        context_text="\n\n".join(blocks),
        results=selected,
        citations=citations,
        estimated_tokens=used,
        diagnostics={"tokens_added": used},
    )
