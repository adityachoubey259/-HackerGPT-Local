"""Ollama local HTTP provider."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from datetime import datetime
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
    ReasoningMode,
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


class OllamaProvider:
    provider_type = ProviderType.OLLAMA
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
        self.display_name = config.label or "Ollama"
        self.enabled = config.enabled
        self._config = config
        self._policy = policy
        self._transport = transport

    def _client(self, timeout: float) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._config.base_url,
            timeout=timeout,
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
                response = await client.get("/api/version")
            if response.status_code >= 400:
                return self._health(ProviderHealthStatus.UNAVAILABLE, "Ollama API is unavailable.")
            payload = response.json()
            version = payload.get("version") if isinstance(payload, dict) else None
            details = {"version": str(version)} if version else {}
            return self._health(ProviderHealthStatus.HEALTHY, "Ollama is reachable.", details)
        except ProviderConfigurationError as exc:
            return self._health(ProviderHealthStatus.MISCONFIGURED, str(exc))
        except httpx.TimeoutException:
            return self._health(ProviderHealthStatus.UNAVAILABLE, "Ollama health check timed out.")
        except (httpx.ConnectError, httpx.NetworkError):
            return self._health(ProviderHealthStatus.UNAVAILABLE, "Ollama is not reachable.")
        except ValueError:
            return self._health(ProviderHealthStatus.DEGRADED, "Ollama returned malformed JSON.")

    async def list_models(self) -> list[NormalizedModel]:
        self._ensure_enabled()
        self._ensure_allowed()
        try:
            async with self._client(self._config.list_timeout_seconds) as client:
                tags_response = await client.get("/api/tags")
                ps_response = await client.get("/api/ps")
        except httpx.TimeoutException as exc:
            raise ModelRequestTimeoutError("Ollama model listing timed out.") from exc
        except (httpx.ConnectError, httpx.NetworkError) as exc:
            raise ProviderUnavailableError("Ollama is not reachable.") from exc
        if tags_response.status_code >= 400:
            raise ProviderUnavailableError("Ollama model listing failed.")
        try:
            tags_payload = tags_response.json()
            ps_payload = ps_response.json() if ps_response.status_code < 400 else {}
        except ValueError as exc:
            raise ProviderResponseError("Ollama returned malformed model data.") from exc
        models = tags_payload.get("models") if isinstance(tags_payload, dict) else None
        if not isinstance(models, list):
            raise ProviderResponseError("Ollama model list response is missing models.")
        running = self._running_model_ids(ps_payload)
        return [self._normalize_model(item, running) for item in models if isinstance(item, dict)]

    async def get_model(self, model_id: str) -> NormalizedModel:
        models = await self.list_models()
        for model in models:
            if model.provider_model_id == model_id or model.id == model_id:
                return model
        raise ModelNotFoundError(f"Ollama model was not found: {model_id}")

    async def generate(
        self,
        model_id: str,
        prompt: str,
        settings: GenerationSettings,
    ) -> ModelTestResponse:
        self._ensure_enabled()
        self._ensure_allowed()
        started = time.perf_counter()
        options: dict[str, float | int] = {
            "temperature": settings.temperature,
            "top_p": settings.top_p,
            "num_predict": settings.max_output_tokens,
        }
        payload: dict[str, Any] = {
            "model": model_id,
            "prompt": prompt,
            "stream": False,
            "options": options,
        }
        if settings.seed is not None:
            options["seed"] = settings.seed
        try:
            async with self._client(self._config.generation_timeout_seconds) as client:
                response = await client.post("/api/generate", json=payload)
        except httpx.TimeoutException as exc:
            raise ModelRequestTimeoutError("Ollama generation timed out.") from exc
        except (httpx.ConnectError, httpx.NetworkError) as exc:
            raise ProviderUnavailableError("Ollama is not reachable.") from exc
        if response.status_code == 404:
            raise ModelNotFoundError(f"Ollama model was not found: {model_id}")
        if response.status_code >= 400:
            raise ProviderResponseError("Ollama generation failed.")
        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderResponseError("Ollama returned malformed generation data.") from exc
        text = data.get("response") if isinstance(data, dict) else None
        if not isinstance(text, str):
            raise ProviderResponseError("Ollama generation response is missing text.")
        duration_ms = round((time.perf_counter() - started) * 1000, 3)
        usage = TokenUsage(
            prompt_tokens=self._int_or_none(data.get("prompt_eval_count")),
            completion_tokens=self._int_or_none(data.get("eval_count")),
        )
        if usage.prompt_tokens is not None or usage.completion_tokens is not None:
            usage.total_tokens = (usage.prompt_tokens or 0) + (usage.completion_tokens or 0)
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
        options: dict[str, float | int] = {
            "temperature": settings.temperature,
            "top_p": settings.top_p,
            "num_predict": settings.max_output_tokens,
        }
        if settings.seed is not None:
            options["seed"] = settings.seed
        payload: dict[str, Any] = {
            "model": model_id,
            "messages": [
                {"role": message.role.value, "content": message.content} for message in messages
            ],
            "stream": True,
            "think": self._should_enable_thinking(settings),
            "options": options,
        }
        try:
            async with self._client(self._config.generation_timeout_seconds) as client:
                async with client.stream("POST", "/api/chat", json=payload) as response:
                    if response.status_code == 404:
                        raise ModelNotFoundError(f"Ollama model was not found: {model_id}")
                    if response.status_code >= 400:
                        raise ProviderResponseError("Ollama streaming generation failed.")
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        event = self._parse_stream_line(line, model_id)
                        if event is not None:
                            yield event
        except httpx.TimeoutException as exc:
            raise ModelRequestTimeoutError("Ollama streaming generation timed out.") from exc
        except (httpx.ConnectError, httpx.NetworkError) as exc:
            raise ProviderUnavailableError("Ollama is not reachable.") from exc

    def _parse_stream_line(self, line: str, model_id: str) -> LLMStreamEvent | None:
        try:
            data = httpx.Response(200, content=line).json()
        except ValueError as exc:
            raise ProviderResponseError("Ollama returned malformed stream data.") from exc
        if not isinstance(data, dict):
            raise ProviderResponseError("Ollama stream item is malformed.")
        message = data.get("message")
        if isinstance(message, dict) and isinstance(message.get("content"), str):
            text = cast(str, message["content"])
            if text:
                return LLMStreamEvent(type=LLMStreamEventType.DELTA, text=text)
        if data.get("done") is True:
            prompt_tokens = self._int_or_none(data.get("prompt_eval_count"))
            completion_tokens = self._int_or_none(data.get("eval_count"))
            total_tokens = (
                (prompt_tokens or 0) + (completion_tokens or 0)
                if prompt_tokens is not None or completion_tokens is not None
                else None
            )
            usage = TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            )
            eval_duration_ns = self._int_or_none(data.get("eval_duration"))
            duration_ms = (eval_duration_ns / 1_000_000) if eval_duration_ns else 0.0
            tokens_per_second = None
            if completion_tokens is not None and eval_duration_ns:
                tokens_per_second = completion_tokens / (eval_duration_ns / 1_000_000_000)
            metrics = ModelCallMetrics(
                provider=self.provider_id,
                model=model_id,
                duration_ms=round(duration_ms, 3),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                tokens_per_second=round(tokens_per_second, 3)
                if tokens_per_second is not None
                else None,
                success=True,
            )
            return LLMStreamEvent(
                type=LLMStreamEventType.DONE,
                usage=usage,
                metrics=metrics,
                finish_reason=data.get("done_reason")
                if isinstance(data.get("done_reason"), str)
                else "stop",
            )
        return None

    def _should_enable_thinking(self, settings: GenerationSettings) -> bool:
        if settings.reasoning_mode is ReasoningMode.FAST:
            return False
        if settings.reasoning_mode is ReasoningMode.DEEP:
            return self._config.reasoning_enabled and settings.max_output_tokens >= 1024
        return False

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
            raise ProviderUnavailableError("Ollama provider is disabled.")

    def _running_model_ids(self, payload: Any) -> set[str]:
        models = payload.get("models") if isinstance(payload, dict) else None
        if not isinstance(models, list):
            return set()
        running: set[str] = set()
        for item in models:
            if isinstance(item, dict) and isinstance(item.get("name"), str):
                running.add(item["name"])
                if isinstance(item.get("model"), str):
                    running.add(item["model"])
        return running

    def _normalize_model(self, item: dict[str, Any], running: set[str]) -> NormalizedModel:
        name = str(item.get("name") or item.get("model") or "")
        details = (
            cast(dict[str, Any], item.get("details"))
            if isinstance(item.get("details"), dict)
            else {}
        )
        override = self._config.model_overrides.get(name)
        modified_at = self._parse_datetime(item.get("modified_at"))
        size_bytes = self._int_or_none(item.get("size"))
        parameter_count = self._string_or_none(details.get("parameter_size"))
        quantization = self._string_or_none(details.get("quantization_level"))
        family = self._string_or_none(details.get("family"))
        if override is not None:
            parameter_count = override.parameter_count or parameter_count
            quantization = override.quantization or quantization
            family = override.family or family
        return NormalizedModel(
            id=f"{self.provider_id}:{name}",
            name=override.friendly_name if override and override.friendly_name else name,
            provider=self.provider_id,
            provider_model_id=name,
            family=family,
            architecture=override.architecture if override else None,
            parameter_count=parameter_count,
            quantization=quantization,
            context_length=override.context_length if override else None,
            size_bytes=size_bytes,
            estimated_ram_bytes=override.estimated_ram_bytes if override else None,
            estimated_vram_bytes=override.estimated_vram_bytes if override else None,
            capabilities=sorted(self.capabilities),
            modified_at=modified_at,
            loaded=name in running,
            metadata={
                "digest": item.get("digest"),
                "metadata_sources": ["provider", "config_override"] if override else ["provider"],
            },
        )

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if not isinstance(value, str):
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    @staticmethod
    def _int_or_none(value: Any) -> int | None:
        return value if isinstance(value, int) else None

    @staticmethod
    def _string_or_none(value: Any) -> str | None:
        return value if isinstance(value, str) and value else None
