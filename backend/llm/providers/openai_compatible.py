"""OpenAI-compatible endpoint providers."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Any, cast

import httpx

from backend.core.policy import PolicyConfig
from backend.llm.domain import (
    GenerationSettings,
    LLMMessage,
    LLMStreamEvent,
    LLMStreamEventType,
    ModelCallMetrics,
    ModelTestResponse,
    NormalizedModel,
    ProviderCapability,
    ProviderConfig,
    ProviderHealth,
    ProviderHealthStatus,
    ProviderType,
    TokenUsage,
)
from backend.llm.errors import (
    ModelNotFoundError,
    ModelRequestTimeoutError,
    ProviderConfigurationError,
    ProviderResponseError,
    ProviderUnavailableError,
)
from backend.llm.network_policy import ensure_provider_network_allowed


class OpenAICompatibleProvider:
    provider_type = ProviderType.OPENAI_COMPATIBLE
    capabilities = frozenset(
        {
            ProviderCapability.CHAT,
            ProviderCapability.COMPLETION,
            ProviderCapability.STREAMING,
            ProviderCapability.MODEL_DISCOVERY,
        }
    )

    def __init__(
        self,
        provider_id: str,
        config: ProviderConfig,
        policy: PolicyConfig,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.provider_id = provider_id
        self.display_name = config.label or "OpenAI-compatible"
        self.enabled = config.enabled
        self._config = config
        self._policy = policy
        self._transport = transport

    def _client(self, timeout: float) -> httpx.AsyncClient:
        headers = {}
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"
        return httpx.AsyncClient(
            base_url=self._config.base_url,
            timeout=timeout,
            headers=headers,
            transport=self._transport,
        )

    def _ensure_allowed(self) -> None:
        ensure_provider_network_allowed(self._config.base_url, self._policy)

    async def health(self) -> ProviderHealth:
        if not self.enabled:
            return self._health(ProviderHealthStatus.DISABLED, "Provider is disabled.")
        try:
            self._ensure_allowed()
            async with self._client(self._config.health_timeout_seconds) as client:
                response = await client.get("/models")
            if response.status_code >= 400:
                return self._health(ProviderHealthStatus.UNAVAILABLE, "Provider models API failed.")
            return self._health(ProviderHealthStatus.HEALTHY, "Provider is reachable.")
        except ProviderConfigurationError as exc:
            return self._health(ProviderHealthStatus.MISCONFIGURED, str(exc))
        except httpx.TimeoutException:
            return self._health(
                ProviderHealthStatus.UNAVAILABLE,
                "Provider health check timed out.",
            )
        except (httpx.ConnectError, httpx.NetworkError):
            return self._health(ProviderHealthStatus.UNAVAILABLE, "Provider is not reachable.")

    async def list_models(self) -> list[NormalizedModel]:
        self._ensure_enabled()
        self._ensure_allowed()
        try:
            async with self._client(self._config.list_timeout_seconds) as client:
                response = await client.get("/models")
        except httpx.TimeoutException as exc:
            raise ModelRequestTimeoutError("Provider model listing timed out.") from exc
        except (httpx.ConnectError, httpx.NetworkError) as exc:
            raise ProviderUnavailableError("Provider is not reachable.") from exc
        if response.status_code >= 400:
            raise ProviderUnavailableError("Provider model listing failed.")
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderResponseError("Provider returned malformed model data.") from exc
        models = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(models, list):
            raise ProviderResponseError("Provider model list response is missing data.")
        return [self._normalize_model(item) for item in models if isinstance(item, dict)]

    async def get_model(self, model_id: str) -> NormalizedModel:
        for model in await self.list_models():
            if model.provider_model_id == model_id or model.id == model_id:
                return model
        raise ModelNotFoundError(f"Model was not found: {model_id}")

    async def generate(
        self,
        model_id: str,
        prompt: str,
        settings: GenerationSettings,
    ) -> ModelTestResponse:
        self._ensure_enabled()
        self._ensure_allowed()
        started = time.perf_counter()
        payload: dict[str, Any] = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": settings.temperature,
            "top_p": settings.top_p,
            "max_tokens": settings.max_output_tokens,
            "stream": False,
        }
        if settings.seed is not None:
            payload["seed"] = settings.seed
        try:
            async with self._client(self._config.generation_timeout_seconds) as client:
                response = await client.post("/chat/completions", json=payload)
        except httpx.TimeoutException as exc:
            raise ModelRequestTimeoutError("Provider generation timed out.") from exc
        except (httpx.ConnectError, httpx.NetworkError) as exc:
            raise ProviderUnavailableError("Provider is not reachable.") from exc
        if response.status_code == 404:
            raise ModelNotFoundError(f"Model was not found: {model_id}")
        if response.status_code >= 400:
            raise ProviderResponseError("Provider generation failed.")
        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderResponseError("Provider returned malformed generation data.") from exc
        text = self._extract_text(data)
        duration_ms = round((time.perf_counter() - started) * 1000, 3)
        usage_payload = data.get("usage") if isinstance(data, dict) else {}
        if not isinstance(usage_payload, dict):
            usage_payload = {}
        usage = TokenUsage(
            prompt_tokens=self._int_or_none(usage_payload.get("prompt_tokens")),
            completion_tokens=self._int_or_none(usage_payload.get("completion_tokens")),
            total_tokens=self._int_or_none(usage_payload.get("total_tokens")),
        )
        tokens_per_second = None
        if usage.completion_tokens is not None and duration_ms > 0:
            tokens_per_second = round(usage.completion_tokens / (duration_ms / 1000), 3)
        metrics = ModelCallMetrics(
            provider=self.provider_id,
            model=model_id,
            duration_ms=duration_ms,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
            tokens_per_second=tokens_per_second,
            success=True,
        )
        return ModelTestResponse(
            provider=self.provider_id,
            model=model_id,
            text=text,
            duration_ms=duration_ms,
            usage=usage,
            metrics=metrics,
        )

    async def stream_chat(
        self,
        model_id: str,
        messages: list[LLMMessage],
        settings: GenerationSettings,
    ) -> AsyncIterator[LLMStreamEvent]:
        self._ensure_enabled()
        self._ensure_allowed()
        payload: dict[str, Any] = {
            "model": model_id,
            "messages": [
                {"role": message.role.value, "content": message.content} for message in messages
            ],
            "temperature": settings.temperature,
            "top_p": settings.top_p,
            "max_tokens": settings.max_output_tokens,
            "stream": True,
        }
        if settings.seed is not None:
            payload["seed"] = settings.seed
        try:
            async with self._client(self._config.generation_timeout_seconds) as client:
                async with client.stream("POST", "/chat/completions", json=payload) as response:
                    if response.status_code == 404:
                        raise ModelNotFoundError(f"Model was not found: {model_id}")
                    if response.status_code >= 400:
                        raise ProviderResponseError("Provider streaming generation failed.")
                    async for line in response.aiter_lines():
                        if not line or line.startswith(":"):
                            continue
                        if not line.startswith("data:"):
                            continue
                        data = line.removeprefix("data:").strip()
                        if data == "[DONE]":
                            yield LLMStreamEvent(
                                type=LLMStreamEventType.DONE,
                                finish_reason="stop",
                            )
                            continue
                        event = self._parse_sse_data(data)
                        if event is not None:
                            yield event
        except httpx.TimeoutException as exc:
            raise ModelRequestTimeoutError("Provider streaming generation timed out.") from exc
        except (httpx.ConnectError, httpx.NetworkError) as exc:
            raise ProviderUnavailableError("Provider is not reachable.") from exc

    def _parse_sse_data(self, data: str) -> LLMStreamEvent | None:
        try:
            payload = httpx.Response(200, content=data).json()
        except ValueError as exc:
            raise ProviderResponseError("Provider returned malformed stream data.") from exc
        if not isinstance(payload, dict):
            raise ProviderResponseError("Provider stream item is malformed.")
        usage_payload = payload.get("usage")
        if isinstance(usage_payload, dict):
            usage = TokenUsage(
                prompt_tokens=self._int_or_none(usage_payload.get("prompt_tokens")),
                completion_tokens=self._int_or_none(usage_payload.get("completion_tokens")),
                total_tokens=self._int_or_none(usage_payload.get("total_tokens")),
            )
            return LLMStreamEvent(type=LLMStreamEventType.USAGE, usage=usage)
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            return None
        first = choices[0]
        if not isinstance(first, dict):
            return None
        finish_reason = first.get("finish_reason")
        delta = first.get("delta")
        if isinstance(delta, dict) and isinstance(delta.get("content"), str):
            text = cast(str, delta["content"])
            if text:
                return LLMStreamEvent(type=LLMStreamEventType.DELTA, text=text)
        if isinstance(finish_reason, str):
            return LLMStreamEvent(
                type=LLMStreamEventType.DONE,
                finish_reason=finish_reason,
            )
        return None

    def _normalize_model(self, item: dict[str, Any]) -> NormalizedModel:
        model_id = str(item.get("id") or "")
        override = self._config.model_overrides.get(model_id)
        return NormalizedModel(
            id=f"{self.provider_id}:{model_id}",
            name=override.friendly_name if override and override.friendly_name else model_id,
            provider=self.provider_id,
            provider_model_id=model_id,
            family=override.family if override else None,
            architecture=override.architecture if override else None,
            parameter_count=override.parameter_count if override else None,
            quantization=override.quantization if override else None,
            context_length=override.context_length if override else None,
            estimated_ram_bytes=override.estimated_ram_bytes if override else None,
            estimated_vram_bytes=override.estimated_vram_bytes if override else None,
            capabilities=sorted(self.capabilities),
            metadata={
                "metadata_sources": ["provider", "config_override"] if override else ["provider"]
            },
        )

    def _health(
        self,
        status: ProviderHealthStatus,
        message: str,
        details: dict[str, str] | None = None,
    ) -> ProviderHealth:
        return ProviderHealth(
            provider=self.provider_id,
            type=self.provider_type,
            status=status,
            message=message,
            capabilities=sorted(self.capabilities),
            base_url=self._config.base_url,
            details=details or {},
        )

    def _ensure_enabled(self) -> None:
        if not self.enabled:
            raise ProviderUnavailableError("Provider is disabled.")

    @staticmethod
    def _extract_text(data: Any) -> str:
        choices = data.get("choices") if isinstance(data, dict) else None
        if not isinstance(choices, list) or not choices:
            raise ProviderResponseError("Provider generation response is missing choices.")
        first = choices[0]
        if not isinstance(first, dict):
            raise ProviderResponseError("Provider generation choice is malformed.")
        message = first.get("message")
        if isinstance(message, dict) and isinstance(message.get("content"), str):
            return cast(str, message["content"])
        text = first.get("text")
        if isinstance(text, str):
            return text
        raise ProviderResponseError("Provider generation response is missing text.")

    @staticmethod
    def _int_or_none(value: Any) -> int | None:
        return value if isinstance(value, int) else None


class LlamaCppProvider(OpenAICompatibleProvider):
    provider_type = ProviderType.LLAMA_CPP


class VLLMProvider(OpenAICompatibleProvider):
    provider_type = ProviderType.VLLM
