"""Provider-independent, local-first model routing."""

from __future__ import annotations

from collections.abc import Iterable
from urllib.parse import urlsplit

from backend.agents.models import AgentDefinition
from backend.core.policy import PolicyConfig
from backend.intelligence.models import (
    HardwareFit,
    ModelCandidate,
    ModelCapabilityProfile,
    RouterMode,
    RoutingDecision,
    RoutingRequest,
    TaskCategory,
)
from backend.intelligence.profiles import ModelProfileRegistry
from backend.intelligence.task_classifier import classify_task
from backend.llm.domain import ModelFit, NormalizedModel, ProviderCapability, ProviderHealth
from backend.system.hardware import HardwareReport

TASK_STRENGTHS: dict[TaskCategory, tuple[str, ...]] = {
    TaskCategory.CODING: ("coding", "code", "programming"),
    TaskCategory.DEBUGGING: ("debugging", "coding"),
    TaskCategory.FRONTEND: ("frontend", "coding", "typescript", "react"),
    TaskCategory.BACKEND: ("backend", "coding", "api"),
    TaskCategory.DATABASE: ("database", "sql"),
    TaskCategory.API_DESIGN: ("api", "structured-output"),
    TaskCategory.SDK_DEVELOPMENT: ("sdk", "coding"),
    TaskCategory.SYSTEM_DESIGN: ("reasoning", "architecture"),
    TaskCategory.DEVOPS: ("devops", "linux"),
    TaskCategory.DATA_ANALYSIS: ("data", "analysis"),
    TaskCategory.RESEARCH: ("research", "long-context"),
    TaskCategory.CYBERSECURITY: ("security", "cybersecurity", "coding", "reasoning"),
    TaskCategory.REVERSE_ENGINEERING: ("reverse-engineering", "security", "reasoning"),
    TaskCategory.MALWARE_ANALYSIS: ("malware", "security", "reasoning"),
    TaskCategory.PROMPT_ENGINEERING: ("prompt", "instruction-following"),
    TaskCategory.LONG_CONTEXT: ("long-context",),
    TaskCategory.REASONING: ("reasoning",),
    TaskCategory.TOOL_USE: ("tool", "function-calling"),
}

LOCAL_PROVIDER_TYPES = {"ollama", "llama_cpp"}


class ModelRouter:
    def __init__(self, policy: PolicyConfig, profiles: ModelProfileRegistry) -> None:
        self._policy = policy
        self._profiles = profiles

    def route(
        self,
        request: RoutingRequest,
        *,
        models: list[NormalizedModel],
        providers: list[ProviderHealth],
        hardware: HardwareReport,
        agent: AgentDefinition | None = None,
    ) -> RoutingDecision:
        task = classify_task(request.message, explicit=request.explicit_task, agent=agent)
        provider_map = {provider.provider: provider for provider in providers}
        if request.manual_provider or request.manual_model or request.mode == RouterMode.MANUAL:
            return self._manual_decision(request, task, models, provider_map)

        candidates: list[ModelCandidate] = []
        for model in models:
            provider = provider_map.get(model.provider)
            if not _provider_available(provider):
                continue
            candidate = self._candidate(model, provider, task, request, hardware, agent)
            if candidate is not None:
                candidates.append(candidate)
        if request.mode == RouterMode.LOCAL_ONLY or self._policy.privacy.local_first:
            local_candidates = [candidate for candidate in candidates if candidate.local]
            if local_candidates:
                candidates = local_candidates
        if request.mode == RouterMode.LOW_MEMORY:
            candidates = [
                candidate
                for candidate in candidates
                if candidate.hardware_fit
                in {HardwareFit.EXCELLENT, HardwareFit.GOOD, HardwareFit.POSSIBLE_SLOWER}
            ]
        if not self._policy.model_routing.cloud_fallback_enabled:
            candidates = [candidate for candidate in candidates if candidate.local]

        candidates.sort(key=lambda item: item.score, reverse=True)
        selected = candidates[0] if candidates else None
        diagnostics = [
            f"task={task.value}",
            f"mode={request.mode.value}",
            "manual=false",
            "cloud_fallback=false"
            if not self._policy.model_routing.cloud_fallback_enabled
            else "cloud_fallback=policy-enabled",
        ]
        if selected is not None:
            diagnostics.append(
                f"selected {selected.provider}/{selected.model} because "
                + "; ".join(selected.reasons[:4])
            )
        return RoutingDecision(
            provider=selected.provider if selected else None,
            model=selected.model if selected else None,
            mode=request.mode,
            task=task,
            manual=False,
            candidates=candidates[:8],
            diagnostics=diagnostics,
            error=None if selected else "No policy-allowed capable model is currently available.",
        )

    def _manual_decision(
        self,
        request: RoutingRequest,
        task: TaskCategory,
        models: list[NormalizedModel],
        providers: dict[str, ProviderHealth],
    ) -> RoutingDecision:
        provider = request.manual_provider
        model = request.manual_model
        if provider is None or model is None:
            return RoutingDecision(
                provider=provider,
                model=model,
                mode=RouterMode.MANUAL,
                task=task,
                manual=True,
                candidates=[],
                diagnostics=["manual=true", "manual provider/model must both be supplied"],
                error="Manual routing requires provider and model.",
            )
        health = providers.get(provider)
        model_known = any(
            item.provider == provider and item.provider_model_id == model for item in models
        )
        diagnostics = ["manual=true", f"task={task.value}"]
        if not _provider_available(health):
            return RoutingDecision(
                provider=provider,
                model=model,
                mode=RouterMode.MANUAL,
                task=task,
                manual=True,
                candidates=[],
                diagnostics=diagnostics,
                error="Manual provider is not available.",
            )
        if not model_known:
            diagnostics.append("model not present in discovery; preserving explicit user choice")
        return RoutingDecision(
            provider=provider,
            model=model,
            mode=RouterMode.MANUAL,
            task=task,
            manual=True,
            candidates=[],
            diagnostics=diagnostics,
        )

    def _candidate(
        self,
        model: NormalizedModel,
        provider: ProviderHealth | None,
        task: TaskCategory,
        request: RoutingRequest,
        hardware: HardwareReport,
        agent: AgentDefinition | None,
    ) -> ModelCandidate | None:
        if provider is None:
            return None
        profile = self._profiles.match(model.provider_model_id) or self._profiles.match(model.name)
        local = _is_local_provider(provider)
        if request.mode == RouterMode.LOCAL_ONLY and not local:
            return None
        if request.requires_vision and not _has_capability(
            model, ProviderCapability.VISION, profile
        ):
            return None
        if request.requires_tools and not _has_capability(
            model, ProviderCapability.TOOL_CALLING, profile
        ):
            return None
        reasons: list[str] = []
        warnings: list[str] = []
        score = 0.25
        if local:
            score += 0.3
            reasons.append("local provider")
        else:
            warnings.append("external endpoint")
            if not self._policy.model_routing.cloud_fallback_enabled:
                return None
        if agent and agent.preferred_model == model.provider_model_id:
            score += 0.25
            reasons.append("agent preferred model")
        if agent and agent.preferred_provider == model.provider:
            score += 0.1
            reasons.append("agent preferred provider")
        if agent and agent.id == "cybersecurity":
            profile_strengths = set(profile.strengths if profile else [])
            if {"security", "coding", "reasoning", "long-context"} & profile_strengths:
                score += 0.12
                reasons.append("ethical hacking agent capability preference")
        strength_score = _profile_strength_score(profile, task, model)
        score += strength_score
        if strength_score:
            reasons.append("task capability profile match")
        fit = _hardware_fit(model, profile, hardware)
        score += _fit_score(fit)
        reasons.append(f"hardware fit {fit.value}")
        if request.mode == RouterMode.QUALITY_FIRST:
            score += (profile.reasoning_score if profile else 0.5) * 0.25
        if request.mode == RouterMode.SPEED_FIRST:
            score += (profile.speed_score if profile else 0.5) * 0.25
        if request.mode == RouterMode.LOW_MEMORY and fit not in {
            HardwareFit.EXCELLENT,
            HardwareFit.GOOD,
        }:
            score -= 0.3
            warnings.append("low-memory mode penalized this fit")
        if request.min_context_tokens and (model.context_length or 0) >= request.min_context_tokens:
            score += 0.15
            reasons.append("context requirement satisfied")
        elif request.min_context_tokens:
            score -= 0.25
            warnings.append("context length may be insufficient")
        return ModelCandidate(
            provider=model.provider,
            model=model.provider_model_id,
            display_name=model.name,
            score=round(score, 4),
            hardware_fit=fit,
            local=local,
            reasons=reasons,
            warnings=warnings,
        )


def _provider_available(provider: ProviderHealth | None) -> bool:
    if provider is None:
        return False
    return provider.status.value in {"healthy", "configured"}


def _is_local_provider(provider: ProviderHealth) -> bool:
    if provider.type.value in LOCAL_PROVIDER_TYPES:
        return True
    if provider.base_url is None:
        return False
    host = urlsplit(provider.base_url).hostname or ""
    return host in {"127.0.0.1", "localhost", "::1"}


def _has_capability(
    model: NormalizedModel,
    capability: ProviderCapability,
    profile: ModelCapabilityProfile | None,
) -> bool:
    if capability in model.capabilities:
        return True
    if capability == ProviderCapability.VISION and profile and profile.vision is True:
        return True
    if capability == ProviderCapability.TOOL_CALLING and profile and profile.tool_support is True:
        return True
    return False


def _profile_strength_score(
    profile: ModelCapabilityProfile | None,
    task: TaskCategory,
    model: NormalizedModel,
) -> float:
    expected = TASK_STRENGTHS.get(task, ())
    metadata = " ".join(str(value).lower() for value in model.metadata.values())
    name = f"{model.name} {model.provider_model_id} {metadata}".lower()
    score = 0.0
    if profile is not None:
        strengths = {strength.lower() for strength in profile.strengths}
        score += sum(0.08 for strength in expected if strength in strengths)
        if task in {
            TaskCategory.CODING,
            TaskCategory.DEBUGGING,
            TaskCategory.FRONTEND,
            TaskCategory.BACKEND,
        }:
            score += profile.coding_score * 0.25
        elif task in {TaskCategory.REASONING, TaskCategory.SYSTEM_DESIGN, TaskCategory.RESEARCH}:
            score += profile.reasoning_score * 0.25
    score += sum(0.04 for strength in expected if strength.replace("-", " ") in name)
    return min(score, 0.5)


def _hardware_fit(
    model: NormalizedModel,
    profile: ModelCapabilityProfile | None,
    hardware: HardwareReport,
) -> HardwareFit:
    required_vram = (
        profile.estimated_vram_bytes if profile and profile.estimated_vram_bytes else None
    ) or model.estimated_vram_bytes
    required_ram = (
        (profile.estimated_ram_bytes if profile and profile.estimated_ram_bytes else None)
        or model.estimated_ram_bytes
        or model.size_bytes
    )
    total_ram = hardware.memory.total_bytes or 0
    available_ram = hardware.memory.available_bytes or total_ram
    vram = max((gpu.vram_total_bytes or 0 for gpu in hardware.gpus), default=0)
    if required_vram and vram:
        if required_vram <= vram * 0.75:
            return HardwareFit.EXCELLENT
        if required_vram <= vram:
            return HardwareFit.GOOD
        if required_ram and required_ram <= available_ram * 0.75:
            return HardwareFit.CPU_HEAVY
        return HardwareFit.NOT_RECOMMENDED
    if model.suitability == ModelFit.EXCELLENT:
        return HardwareFit.EXCELLENT
    if model.suitability == ModelFit.SUITABLE:
        return HardwareFit.GOOD
    if model.suitability == ModelFit.CONSTRAINED:
        return HardwareFit.POSSIBLE_SLOWER
    if model.suitability == ModelFit.CPU_PARTIAL_OFFLOAD:
        return HardwareFit.CPU_HEAVY
    if model.suitability == ModelFit.NOT_RECOMMENDED:
        return HardwareFit.NOT_RECOMMENDED
    if required_ram and available_ram:
        if required_ram <= available_ram * 0.45:
            return HardwareFit.GOOD
        if required_ram <= available_ram * 0.75:
            return HardwareFit.POSSIBLE_SLOWER
        if required_ram <= total_ram * 0.9:
            return HardwareFit.CPU_HEAVY
        return HardwareFit.NOT_RECOMMENDED
    return HardwareFit.UNKNOWN


def _fit_score(fit: HardwareFit) -> float:
    return {
        HardwareFit.EXCELLENT: 0.25,
        HardwareFit.GOOD: 0.18,
        HardwareFit.POSSIBLE_SLOWER: 0.06,
        HardwareFit.CPU_HEAVY: -0.05,
        HardwareFit.NOT_RECOMMENDED: -0.5,
        HardwareFit.UNKNOWN: 0.0,
    }[fit]


def provider_ids(providers: Iterable[ProviderHealth]) -> set[str]:
    return {provider.provider for provider in providers}
