"""Provider factory."""

from __future__ import annotations

from backend.core.policy import PolicyConfig
from backend.llm.domain import ModelProviderConfiguration, ProviderType
from backend.llm.providers.base import BaseLLMProvider
from backend.llm.providers.ollama import OllamaProvider
from backend.llm.providers.openai_compatible import (
    LlamaCppProvider,
    OpenAICompatibleProvider,
    VLLMProvider,
)
from backend.llm.providers.registry import LLMProviderRegistry


def build_provider_registry(
    config: ModelProviderConfiguration,
    policy: PolicyConfig,
) -> LLMProviderRegistry:
    providers: list[BaseLLMProvider] = []
    for provider_id, provider_config in config.providers.items():
        if provider_config.type == ProviderType.OLLAMA:
            providers.append(OllamaProvider(provider_id, provider_config, policy))
        elif provider_config.type == ProviderType.LLAMA_CPP:
            providers.append(LlamaCppProvider(provider_id, provider_config, policy))
        elif provider_config.type == ProviderType.OPENAI_COMPATIBLE:
            providers.append(OpenAICompatibleProvider(provider_id, provider_config, policy))
        elif provider_config.type == ProviderType.VLLM:
            providers.append(VLLMProvider(provider_id, provider_config, policy))
    return LLMProviderRegistry(providers)
