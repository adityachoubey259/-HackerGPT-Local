"""Policy-controlled live research service."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette import status

from backend.api.errors import ApplicationError
from backend.api.schemas.research import (
    ResearchHistoryResponse,
    ResearchRetrieveRequest,
    ResearchRunRequest,
    ResearchRunResponse,
    ResearchSessionRead,
    ResearchSourceRead,
    ResearchStatusResponse,
    RetrievedPageResponse,
)
from backend.core.policy import PolicyConfig
from backend.core.time import utc_now
from backend.db.models import ResearchCacheEntry, ResearchSession, ResearchSource
from backend.db.repositories.sqlalchemy import (
    LOCAL_USER_ID,
    SqlAlchemyResearchRepository,
    SqlAlchemyUserRepository,
)
from backend.research.models import RetrievedPage, SearchResult
from backend.research.providers import SearchProviderError, build_search_provider
from backend.research.retriever import PageRetriever
from backend.research.safety import ensure_url_allowed


class ResearchService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        policy: PolicyConfig,
    ) -> None:
        self._session_factory = session_factory
        self._policy = policy

    def status(self) -> ResearchStatusResponse:
        research = self._policy.research
        configured = bool(research.searxng_base_url) if research.provider == "searxng" else False
        return ResearchStatusResponse(
            enabled=research.enabled,
            search_enabled=research.search_enabled,
            provider=research.provider,
            configured=configured,
            allowed_domains=research.allowed_domains,
            blocked_domains=research.blocked_domains,
            max_results=research.max_results,
            cache_ttl_seconds=research.cache_ttl_seconds,
            official_sources_preferred=research.official_sources_preferred,
            private_networks_blocked=research.block_private_networks,
        )

    async def history(self, *, limit: int = 30, offset: int = 0) -> ResearchHistoryResponse:
        async with self._session_factory() as session:
            repo = SqlAlchemyResearchRepository(session)
            sessions, total = await repo.list_sessions(LOCAL_USER_ID, limit=limit, offset=offset)
            return ResearchHistoryResponse(
                items=[session_to_read(item) for item in sessions],
                total=total,
            )

    async def run(self, body: ResearchRunRequest) -> ResearchRunResponse:
        requested_results = body.max_results or self._policy.research.max_results
        max_results = min(requested_results, self._policy.research.max_results)
        async with self._session_factory() as session:
            await SqlAlchemyUserRepository(session).get_or_create_local()
            repo = SqlAlchemyResearchRepository(session)
            research_session = await repo.create_session(
                user_id=LOCAL_USER_ID,
                query=body.query.strip(),
                status="running",
                provider=self._policy.research.provider,
                official_only=body.official_only,
                filters={"max_results": max_results},
            )
            await session.commit()
        if not self._policy.research.enabled or not self._policy.research.search_enabled:
            return await self._mark_session(
                research_session.id,
                status="offline",
                answer=(
                    "Live research is disabled by policy. Enable it in config/policy.yaml "
                    "to query external sources."
                ),
                diagnostics={"reason": "policy_disabled"},
            )
        try:
            provider = build_search_provider(self._policy.research)
            search_results = await provider.search(body.query.strip(), max_results=max_results)
        except (SearchProviderError, OSError, ValueError) as exc:
            return await self._mark_session(
                research_session.id,
                status="failed",
                answer="Research provider could not return results.",
                diagnostics={"error": str(exc)},
            )
        sources = await self._record_search_sources(research_session.id, search_results)
        answer = _source_summary(body.query, sources)
        return await self._mark_session(
            research_session.id,
            status="completed",
            answer=answer,
            diagnostics={"source_count": len(sources), "provider": self._policy.research.provider},
        )

    async def run_for_context(self, query: str, *, max_results: int = 3) -> ResearchRunResponse:
        if not self._policy.research.enabled or not self._policy.research.search_enabled:
            return await self.run(
                ResearchRunRequest(query=query, max_results=max_results, official_only=False)
            )
        return await self.run(
            ResearchRunRequest(query=query, max_results=max_results, official_only=False)
        )

    async def retrieve(self, body: ResearchRetrieveRequest) -> RetrievedPageResponse:
        if not self._policy.research.enabled:
            raise ApplicationError(
                "RESEARCH_DISABLED",
                "Live research retrieval is disabled by policy.",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        normalized = ensure_url_allowed(body.url, self._policy.research)
        async with self._session_factory() as session:
            repo = SqlAlchemyResearchRepository(session)
            if body.use_cache:
                cached = await repo.get_cache(normalized)
                if cached is not None and cached.expires_at > utc_now():
                    return cache_to_page_response(cached, from_cache=True)
        page = await PageRetriever(self._policy.research).retrieve(normalized)
        expires_at = page.retrieved_at + timedelta(seconds=self._policy.research.cache_ttl_seconds)
        async with self._session_factory() as session:
            repo = SqlAlchemyResearchRepository(session)
            cache = await repo.upsert_cache(
                normalized_url=page.normalized_url,
                url=page.url,
                domain=page.domain,
                title=page.title,
                content_text=page.content_text,
                excerpt=page.excerpt,
                mime_type=page.mime_type,
                status_code=page.status_code,
                checksum=page.checksum,
                retrieved_at=page.retrieved_at,
                expires_at=expires_at,
                metadata=page.metadata,
            )
            await session.commit()
            return cache_to_page_response(cache, from_cache=False)

    async def _record_search_sources(
        self, session_id: str, results: list[SearchResult]
    ) -> list[ResearchSourceRead]:
        async with self._session_factory() as session:
            repo = SqlAlchemyResearchRepository(session)
            sources: list[ResearchSource] = []
            for index, result in enumerate(results, start=1):
                normalized = ensure_url_allowed(result.url, self._policy.research)
                source = await repo.create_source(
                    user_id=LOCAL_USER_ID,
                    session_id=session_id,
                    citation_id=f"R{index}",
                    url=normalized,
                    normalized_url=normalized,
                    domain=normalized.split("/")[2],
                    title=result.title,
                    excerpt=result.snippet,
                    source_type=result.source_type,
                    reliability=_reliability_for_url(normalized),
                    metadata=result.metadata,
                )
                sources.append(source)
            await session.commit()
            return [source_to_read(item) for item in sources]

    async def _mark_session(
        self,
        session_id: str,
        *,
        status: str,
        answer: str,
        diagnostics: dict[str, Any],
    ) -> ResearchRunResponse:
        async with self._session_factory() as session:
            repo = SqlAlchemyResearchRepository(session)
            research_session = await repo.get_session(LOCAL_USER_ID, session_id)
            if research_session is None:
                raise ApplicationError(
                    "RESEARCH_SESSION_NOT_FOUND",
                    "Research session was not found.",
                    status_code=404,
                )
            await repo.update_session(
                research_session,
                status=status,
                answer=answer,
                diagnostics=diagnostics,
            )
            sources = await repo.list_sources(session_id)
            await session.commit()
            return ResearchRunResponse(
                session=session_to_read(research_session),
                sources=[source_to_read(item) for item in sources],
            )


def session_to_read(session: ResearchSession) -> ResearchSessionRead:
    return ResearchSessionRead(
        id=session.id,
        query=session.query,
        status=session.status,
        provider=session.provider,
        answer=session.answer,
        official_only=session.official_only,
        filters=session.filters,
        diagnostics=session.diagnostics,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


def source_to_read(source: ResearchSource) -> ResearchSourceRead:
    return ResearchSourceRead(
        id=source.id,
        citation_id=source.citation_id,
        url=source.url,
        normalized_url=source.normalized_url,
        domain=source.domain,
        title=source.title,
        source_type=source.source_type,
        reliability=source.reliability,
        excerpt=source.excerpt,
        content_checksum=source.content_checksum,
        retrieved_at=source.retrieved_at,
        metadata=source.metadata_json,
        created_at=source.created_at,
    )


def cache_to_page_response(cache: ResearchCacheEntry, *, from_cache: bool) -> RetrievedPageResponse:
    return RetrievedPageResponse(
        url=cache.url,
        normalized_url=cache.normalized_url,
        domain=cache.domain,
        title=cache.title,
        excerpt=cache.excerpt,
        content_checksum=cache.checksum,
        retrieved_at=cache.retrieved_at,
        from_cache=from_cache,
        diagnostics={
            "mime_type": cache.mime_type,
            "status_code": cache.status_code,
            "expires_at": cache.expires_at.isoformat(),
        },
    )


def page_to_cache_payload(page: RetrievedPage) -> dict[str, Any]:
    return {
        "normalized_url": page.normalized_url,
        "url": page.url,
        "domain": page.domain,
        "title": page.title,
        "content_text": page.content_text,
        "excerpt": page.excerpt,
        "mime_type": page.mime_type,
        "status_code": page.status_code,
        "checksum": page.checksum,
        "retrieved_at": page.retrieved_at,
    }


def _source_summary(query: str, sources: list[ResearchSourceRead]) -> str:
    if not sources:
        return "No policy-allowed sources were returned for this query."
    lines = [f"Research session for: {query}", "", "Candidate sources:"]
    for source in sources:
        lines.append(f"- [{source.citation_id}] {source.title} ({source.domain})")
    return "\n".join(lines)


def _reliability_for_url(url: str) -> str:
    domain = url.split("/")[2].lower()
    if domain.endswith((".gov", ".mil", ".edu")):
        return "official"
    if any(part in domain for part in ("github.com", "docs.", "developer.", "nist.", "cisa.")):
        return "technical-primary"
    return "unverified"
