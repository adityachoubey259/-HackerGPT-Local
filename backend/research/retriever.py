"""Safe web page retrieval and extraction."""

from __future__ import annotations

import hashlib
import html
import re
from datetime import UTC, datetime
from html.parser import HTMLParser

import httpx

from backend.api.errors import ApplicationError
from backend.core.policy import ResearchPolicy
from backend.research.models import RetrievedPage
from backend.research.safety import domain_for_url, ensure_url_allowed


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self._in_title = False
        self._skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "title":
            self._in_title = True
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text:
            return
        if self._in_title:
            self.title = (self.title + " " + text).strip()
        if self._skip_depth == 0:
            self.parts.append(text)

    def content(self) -> str:
        return normalize_text(" ".join(self.parts))


class PageRetriever:
    def __init__(self, policy: ResearchPolicy) -> None:
        self._policy = policy

    async def retrieve(self, url: str) -> RetrievedPage:
        normalized = ensure_url_allowed(url, self._policy)
        async with httpx.AsyncClient(
            timeout=self._policy.request_timeout_seconds,
            follow_redirects=True,
            max_redirects=self._policy.redirect_limit,
        ) as client:
            response = await client.get(normalized)
        final_url = ensure_url_allowed(str(response.url), self._policy)
        content_type = response.headers.get("content-type", "").split(";")[0].lower() or None
        content = response.content[: self._policy.max_download_bytes + 1]
        if len(content) > self._policy.max_download_bytes:
            raise ApplicationError(
                "RESEARCH_RESPONSE_TOO_LARGE",
                "The retrieved document exceeds the configured research size limit.",
                status_code=413,
            )
        response.raise_for_status()
        text = content.decode(response.encoding or "utf-8", errors="replace")
        title = final_url
        if content_type and ("html" in content_type or "xml" in content_type):
            parser = _TextExtractor()
            parser.feed(text)
            title = normalize_text(html.unescape(parser.title))[:500] or final_url
            extracted = parser.content()
        else:
            extracted = normalize_text(text)
        checksum = hashlib.sha256(extracted.encode("utf-8")).hexdigest()
        return RetrievedPage(
            url=final_url,
            normalized_url=final_url,
            domain=domain_for_url(final_url),
            title=title,
            content_text=extracted[: self._policy.max_download_bytes],
            excerpt=extracted[:900],
            mime_type=content_type,
            status_code=response.status_code,
            checksum=checksum,
            retrieved_at=datetime.now(UTC),
            metadata={"bytes_read": len(content)},
        )


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
