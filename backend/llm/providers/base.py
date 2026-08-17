"""Provider-independent LLM provider contract."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from backend.llm.domain import (
    GenerationSettings,
    LLMMessage,
    LLMStreamEvent,
    ModelTestResponse,
    NormalizedModel,
    ProviderCapability,
    ProviderHealth,
    ProviderType,
)


class BaseLLMProvider(Protocol):
    provider_id: str
    provider_type: ProviderType
    display_name: str
    enabled: bool
    capabilities: frozenset[ProviderCapability]

    async def health(self) -> ProviderHealth: ...
    async def list_models(self) -> list[NormalizedModel]: ...
    async def get_model(self, model_id: str) -> NormalizedModel: ...
    async def generate(
        self,
        model_id: str,
        prompt: str,
        settings: GenerationSettings,
    ) -> ModelTestResponse: ...
    def stream_chat(
        self,
        model_id: str,
        messages: list[LLMMessage],
        settings: GenerationSettings,
    ) -> AsyncIterator[LLMStreamEvent]: ...
