"""Model provider services."""

from __future__ import annotations

import math

from backend.llm.domain import (
    ModelFit,
    ModelProviderConfiguration,
    ModelTestRequest,
    ModelTestResponse,
    NormalizedModel,
    ProviderHealth,
)
from backend.llm.errors import ModelNotFoundError, ModelProviderError
from backend.llm.providers.registry import LLMProviderRegistry
from backend.system.hardware import HardwareReport


class ModelSuitabilityService:
    def classify(self, model: NormalizedModel, hardware: HardwareReport) -> ModelFit:
        total_ram = hardware.memory.total_bytes or 0
        largest_vram = max((gpu.vram_total_bytes or 0 for gpu in hardware.gpus), default=0)
        required = model.estimated_vram_bytes or model.size_bytes or model.estimated_ram_bytes
        if required is None:
            return ModelFit.UNKNOWN
        if largest_vram and required <= largest_vram * 0.65:
            return ModelFit.EXCELLENT
        if largest_vram and required <= largest_vram * 0.95:
            return ModelFit.SUITABLE
        if total_ram and required <= total_ram * 0.55:
            return ModelFit.CONSTRAINED
        if total_ram and required <= total_ram * 0.9:
            return ModelFit.CPU_PARTIAL_OFFLOAD
        return ModelFit.NOT_RECOMMENDED

    def estimate_from_parameter_count(self, parameter_count: str | None) -> int | None:
        if not parameter_count:
            return None
        normalized = parameter_count.strip().lower().replace("parameters", "").strip()
        multiplier = 1
        if normalized.endswith("b"):
            multiplier = 1_000_000_000
            normalized = normalized[:-1]
        elif normalized.endswith("m"):
            multiplier = 1_000_000
            normalized = normalized[:-1]
        try:
            params = float(normalized) * multiplier
        except ValueError:
            return None
        return math.ceil(params * 0.65)


class ModelService:
    def __init__(
        self,
        registry: LLMProviderRegistry,
        model_config: ModelProviderConfiguration,
        suitability: ModelSuitabilityService,
    ) -> None:
        self._registry = registry
        self._model_config = model_config
        self._suitability = suitability

    async def providers(self) -> list[ProviderHealth]:
        return await self._registry.health()

    async def list_models(
        self,
        hardware: HardwareReport,
        provider_id: str | None = None,
    ) -> list[NormalizedModel]:
        providers = [self._registry.get(provider_id)] if provider_id else self._registry.providers()
        models: list[NormalizedModel] = []
        for provider in providers:
            if not provider.enabled:
                continue
            try:
                provider_models = await provider.list_models()
            except ModelProviderError:
                if provider_id is not None:
                    raise
                continue
            models.extend(self._with_suitability(model, hardware) for model in provider_models)
        return models

    async def get_model(
        self,
        provider_id: str,
        model_id: str,
        hardware: HardwareReport,
    ) -> NormalizedModel:
        provider = self._registry.get(provider_id)
        model = await provider.get_model(model_id)
        return self._with_suitability(model, hardware)

    async def test_model(self, request: ModelTestRequest) -> ModelTestResponse:
        provider = self._registry.get(request.provider)
        return await provider.generate(request.model, request.prompt, request.settings)

    def defaults(self) -> dict[str, str | None]:
        return {
            "provider": self._model_config.default_provider,
            "model": self._model_config.default_model,
        }

    def _with_suitability(
        self,
        model: NormalizedModel,
        hardware: HardwareReport,
    ) -> NormalizedModel:
        estimated = model.estimated_vram_bytes or self._suitability.estimate_from_parameter_count(
            model.parameter_count
        )
        enriched = model.model_copy(update={"estimated_vram_bytes": estimated})
        return enriched.model_copy(
            update={"suitability": self._suitability.classify(enriched, hardware)}
        )


def ensure_model_present(models: list[NormalizedModel], model_id: str) -> NormalizedModel:
    for model in models:
        if model.id == model_id or model.provider_model_id == model_id:
            return model
    raise ModelNotFoundError(f"Model was not found: {model_id}")
