from __future__ import annotations

import json

import httpx
import pytest

from backend.core.policy import PolicyConfig
from backend.llm.domain import (
    GenerationSettings,
    LLMStreamEventType,
    ModelProviderConfiguration,
    ModelTestRequest,
    NormalizedModel,
    ProviderConfig,
    ProviderHealthStatus,
    ProviderType,
    ReasoningMode,
)
from backend.llm.errors import (
    ModelRequestTimeoutError,
    ProviderResponseError,
    ProviderUnavailableError,
)
from backend.llm.providers.ollama import OllamaProvider
from backend.llm.providers.openai_compatible import (
    LlamaCppProvider,
    OpenAICompatibleProvider,
    VLLMProvider,
)
from backend.llm.providers.registry import LLMProviderRegistry
from backend.services.models import ModelService, ModelSuitabilityService
from backend.system.hardware import (
    CpuInfo,
    GpuInfo,
    HardwareReport,
    MemoryInfo,
    RuntimeAccelerationInfo,
)


def _config(provider_type: ProviderType = ProviderType.OLLAMA) -> ProviderConfig:
    return ProviderConfig(type=provider_type, base_url="http://127.0.0.1:11434")


def _hardware() -> HardwareReport:
    return HardwareReport(
        operating_system="Windows",
        architecture="AMD64",
        cpu=CpuInfo(logical_processors=16),
        memory=MemoryInfo(total_bytes=16 * 1024**3, available_bytes=8 * 1024**3),
        gpus=[GpuInfo(name="RTX 4050", vendor="NVIDIA", vram_total_bytes=6 * 1024**3)],
        acceleration=RuntimeAccelerationInfo(cuda_available=True),
    )


async def test_registry_reports_capabilities() -> None:
    provider = OllamaProvider("ollama", _config(), PolicyConfig())
    registry = LLMProviderRegistry([provider])
    assert registry.get("ollama").provider_id == "ollama"


async def test_ollama_health_success() -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(200, json={"version": "0.32.6"})
    )
    provider = OllamaProvider("ollama", _config(), PolicyConfig(), transport)
    health = await provider.health()
    assert health.status is ProviderHealthStatus.HEALTHY
    assert health.details["version"] == "0.32.6"


async def test_ollama_unavailable() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline")

    provider = OllamaProvider("ollama", _config(), PolicyConfig(), httpx.MockTransport(handler))
    health = await provider.health()
    assert health.status is ProviderHealthStatus.UNAVAILABLE


async def test_ollama_timeout() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("slow")

    provider = OllamaProvider("ollama", _config(), PolicyConfig(), httpx.MockTransport(handler))
    with pytest.raises(ModelRequestTimeoutError):
        await provider.list_models()


async def test_ollama_malformed_response() -> None:
    provider = OllamaProvider(
        "ollama",
        _config(),
        PolicyConfig(),
        httpx.MockTransport(lambda _request: httpx.Response(200, json={"wrong": []})),
    )
    with pytest.raises(ProviderResponseError):
        await provider.list_models()


async def test_ollama_model_discovery_and_running_state() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/ps":
            return httpx.Response(200, json={"models": [{"name": "qwen3:8b"}]})
        return httpx.Response(
            200,
            json={
                "models": [
                    {
                        "name": "qwen3:8b",
                        "size": 5_200_000_000,
                        "modified_at": "2026-08-01T00:00:00Z",
                        "details": {
                            "family": "qwen3",
                            "parameter_size": "8B",
                            "quantization_level": "Q4_K_M",
                        },
                    }
                ]
            },
        )

    provider = OllamaProvider("ollama", _config(), PolicyConfig(), httpx.MockTransport(handler))
    models = await provider.list_models()
    assert models[0].provider_model_id == "qwen3:8b"
    assert models[0].loaded is True
    assert models[0].parameter_count == "8B"


async def test_ollama_generation_success() -> None:
    provider = OllamaProvider(
        "ollama",
        _config(),
        PolicyConfig(),
        httpx.MockTransport(
            lambda _request: httpx.Response(
                200,
                json={"response": "hello", "prompt_eval_count": 2, "eval_count": 3},
            )
        ),
    )
    response = await provider.generate("qwen3:8b", "hi", GenerationSettings())
    assert response.text == "hello"
    assert response.usage is not None
    assert response.usage.total_tokens == 5


async def test_ollama_stream_ignores_qwen_thinking_and_emits_visible_content() -> None:
    seen_payload: dict[str, object] = {}
    lines = [
        {
            "message": {
                "role": "assistant",
                "content": "",
                "thinking": "hidden reasoning must not be exposed",
            },
            "done": False,
        },
        {"message": {"role": "assistant", "content": "CHAT"}, "done": False},
        {"message": {"role": "assistant", "content": "_OK"}, "done": False},
        {
            "message": {"role": "assistant", "content": ""},
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": 4,
            "eval_count": 2,
        },
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        seen_payload.update(json.loads(request.content.decode()))
        return httpx.Response(
            200,
            content="\n".join(json.dumps(line) for line in lines),
        )

    provider = OllamaProvider(
        "ollama",
        _config(),
        PolicyConfig(),
        httpx.MockTransport(handler),
    )

    events = [
        event
        async for event in provider.stream_chat(
            "qwen3:8b",
            [],
            GenerationSettings(max_output_tokens=32),
        )
    ]

    assert seen_payload["think"] is False
    assert [event.type for event in events] == [
        LLMStreamEventType.DELTA,
        LLMStreamEventType.DELTA,
        LLMStreamEventType.DONE,
    ]
    assert "".join(event.text or "" for event in events) == "CHAT_OK"
    assert events[-1].usage is not None
    assert events[-1].usage.total_tokens == 6


async def test_ollama_deep_reasoning_requires_provider_enablement_and_budget() -> None:
    payloads: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payloads.append(json.loads(request.content.decode()))
        return httpx.Response(200, content=json.dumps({"done": True, "done_reason": "stop"}))

    provider = OllamaProvider(
        "ollama",
        _config().model_copy(update={"reasoning_enabled": True}),
        PolicyConfig(),
        httpx.MockTransport(handler),
    )

    _ = [
        event
        async for event in provider.stream_chat(
            "qwen3:8b",
            [],
            GenerationSettings(max_output_tokens=512, reasoning_mode=ReasoningMode.DEEP),
        )
    ]
    _ = [
        event
        async for event in provider.stream_chat(
            "qwen3:8b",
            [],
            GenerationSettings(max_output_tokens=1024, reasoning_mode=ReasoningMode.DEEP),
        )
    ]

    assert payloads[0]["think"] is False
    assert payloads[1]["think"] is True


async def test_openai_compatible_model_and_generation() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/models":
            return httpx.Response(200, json={"data": [{"id": "local-model"}]})
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
        )

    provider = OpenAICompatibleProvider(
        "openai_compatible",
        _config(ProviderType.OPENAI_COMPATIBLE),
        PolicyConfig(),
        httpx.MockTransport(handler),
    )
    assert (await provider.list_models())[0].provider_model_id == "local-model"
    assert (await provider.generate("local-model", "test", GenerationSettings())).text == "ok"


async def test_llama_cpp_and_vllm_use_openai_compatible_shape() -> None:
    llama = LlamaCppProvider("llama_cpp", _config(ProviderType.LLAMA_CPP), PolicyConfig())
    vllm = VLLMProvider("vllm", _config(ProviderType.VLLM), PolicyConfig())
    assert llama.provider_type is ProviderType.LLAMA_CPP
    assert vllm.provider_type is ProviderType.VLLM


async def test_no_hidden_fallback_when_provider_fails() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline")

    provider = OllamaProvider("ollama", _config(), PolicyConfig(), httpx.MockTransport(handler))
    registry = LLMProviderRegistry([provider])
    service = ModelService(
        registry,
        model_config=ModelProviderConfiguration(),
        suitability=ModelSuitabilityService(),
    )
    with pytest.raises(ProviderUnavailableError):
        await service.test_model(ModelTestRequest(provider="ollama", model="qwen3:8b", prompt="hi"))


def test_generation_parameters_validate_ranges() -> None:
    with pytest.raises(ValueError):
        GenerationSettings(temperature=3.0)


def test_model_suitability_heuristics() -> None:
    service = ModelSuitabilityService()
    assert service.estimate_from_parameter_count("8B") is not None
    assert service.classify(
        model=NormalizedModel(
            id="ollama:test",
            name="test",
            provider="ollama",
            provider_model_id="test",
            estimated_vram_bytes=3 * 1024**3,
        ),
        hardware=_hardware(),
    ).value in {"excellent", "suitable"}
