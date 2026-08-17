"""Provider-independent LLM adapter protocols for future phases."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ChatRequest:
    model: str
    messages: tuple[ChatMessage, ...]
    temperature: float | None = None
    max_tokens: int | None = None


@dataclass(frozen=True)
class ChatChunk:
    content: str
    done: bool = False


class ChatProvider(Protocol):
    async def complete(self, request: ChatRequest) -> ChatMessage: ...
    async def stream(self, request: ChatRequest) -> AsyncIterator[ChatChunk]: ...
