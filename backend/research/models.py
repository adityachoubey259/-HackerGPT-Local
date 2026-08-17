"""Domain types for policy-controlled web research."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str
    source_type: str = "web"
    reliability: str = "unknown"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievedPage:
    url: str
    normalized_url: str
    domain: str
    title: str
    content_text: str
    excerpt: str
    mime_type: str | None
    status_code: int | None
    checksum: str
    retrieved_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ResearchCitation:
    citation_id: str
    title: str
    url: str
    domain: str
    excerpt: str
    reliability: str
