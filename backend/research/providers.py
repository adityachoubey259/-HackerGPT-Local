"""Search provider adapters for live research."""

from __future__ import annotations

from typing import Any, Protocol

import httpx

from backend.core.policy import ResearchPolicy
from backend.research.models import SearchResult
from backend.research.safety import ensure_url_allowed


class SearchProviderError(Exception):
    """Raised when a search provider cannot return usable results."""


class SearchProvider(Protocol):
    async def search(self, query: str, *, max_results: int) -> list[SearchResult]: ...


class DisabledSearchProvider:
    async def search(self, query: str, *, max_results: int) -> list[SearchResult]:
        raise SearchProviderError("Live search is disabled by policy.")


class SearxngSearchProvider:
    def __init__(self, policy: ResearchPolicy) -> None:
        self._policy = policy
        if not policy.searxng_base_url:
            raise SearchProviderError("SearxNG base URL is not configured.")
        self._base_url = policy.searxng_base_url.rstrip("/")

    async def search(self, query: str, *, max_results: int) -> list[SearchResult]:
        async with httpx.AsyncClient(timeout=self._policy.request_timeout_seconds) as client:
            response = await client.get(
                f"{self._base_url}/search",
                params={"q": query, "format": "json"},
            )
            response.raise_for_status()
            payload = response.json()
        results = payload.get("results", [])
        if not isinstance(results, list):
            raise SearchProviderError("Search provider returned an unexpected payload.")
        parsed: list[SearchResult] = []
        for item in results:
            if not isinstance(item, dict):
                continue
            parsed_item = _parse_result(item, self._policy)
            if parsed_item is not None:
                parsed.append(parsed_item)
            if len(parsed) >= max_results:
                break
        return parsed


def build_search_provider(policy: ResearchPolicy) -> SearchProvider:
    if not policy.enabled or not policy.search_enabled:
        return DisabledSearchProvider()
    if policy.provider == "searxng":
        return SearxngSearchProvider(policy)
    raise SearchProviderError(f"Unsupported research provider: {policy.provider}")


def _parse_result(item: dict[str, Any], policy: ResearchPolicy) -> SearchResult | None:
    url = item.get("url")
    if not isinstance(url, str):
        return None
    try:
        normalized = ensure_url_allowed(url, policy)
    except Exception:
        return None
    raw_title = item.get("title")
    title = raw_title if isinstance(raw_title, str) else normalized
    snippet = ""
    for key in ("content", "snippet", "description"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            snippet = value.strip()
            break
    return SearchResult(
        title=title.strip()[:500],
        url=normalized,
        snippet=snippet[:1500],
        reliability="candidate",
        metadata={"engine": item.get("engine")} if isinstance(item.get("engine"), str) else {},
    )
