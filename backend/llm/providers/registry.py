"""Model provider registry."""

from __future__ import annotations

from backend.llm.domain import ProviderHealth, ProviderHealthStatus
from backend.llm.errors import ProviderUnavailableError
from backend.llm.providers.base import BaseLLMProvider


class LLMProviderRegistry:
    def __init__(self, providers: list[BaseLLMProvider] | None = None) -> None:
        self._providers: dict[str, BaseLLMProvider] = {}
        for provider in providers or []:
            self.register(provider)

    def register(self, provider: BaseLLMProvider) -> None:
        self._providers[provider.provider_id] = provider

    def get(self, provider_id: str) -> BaseLLMProvider:
        provider = self._providers.get(provider_id)
        if provider is None:
            msg = f"Provider is not configured: {provider_id}"
            raise ProviderUnavailableError(msg)
        return provider

    def providers(self) -> list[BaseLLMProvider]:
        return list(self._providers.values())

    async def health(self) -> list[ProviderHealth]:
        statuses: list[ProviderHealth] = []
        for provider in self.providers():
            if not provider.enabled:
                statuses.append(
                    ProviderHealth(
                        provider=provider.provider_id,
                        type=provider.provider_type,
                        status=ProviderHealthStatus.DISABLED,
                        message="Provider is disabled.",
                        capabilities=sorted(provider.capabilities),
                    )
                )
                continue
            statuses.append(await provider.health())
        return statuses
