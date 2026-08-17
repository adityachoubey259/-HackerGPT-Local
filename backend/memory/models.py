"""Memory domain helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MemoryContextItem:
    memory_id: str
    citation_id: str
    title: str
    content: str
    memory_type: str
    scope: str
    relevance: float
