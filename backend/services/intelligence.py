"""Application service for model routing and context diagnostics."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.agents.models import AgentDefinition
from backend.core.policy import PolicyConfig
from backend.intelligence.context import ContextEngine
from backend.intelligence.models import PreparedContext, RoutingDecision, RoutingRequest
from backend.intelligence.profiles import ModelProfileRegistry
from backend.intelligence.router import ModelRouter
from backend.llm.domain import GenerationSettings, ModelProviderConfiguration
from backend.llm.providers.registry import LLMProviderRegistry
from backend.services.agents import AgentService
from backend.services.knowledge import KnowledgeService
from backend.services.memory import MemoryService
from backend.services.models import ModelService
from backend.services.preferences import PreferenceService
from backend.services.prompts import load_system_prompt
from backend.services.research import ResearchService
from backend.system.hardware import cached_hardware_report


class IntelligenceService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        registry: LLMProviderRegistry,
        model_config: ModelProviderConfiguration,
        policy: PolicyConfig,
        model_service: ModelService,
        agent_service: AgentService,
        *,
        workspace_root: Path,
        knowledge_service: KnowledgeService,
        memory_service: MemoryService,
        research_service: ResearchService,
        preference_service: PreferenceService | None = None,
        system_prompt: str | None = None,
    ) -> None:
        self._registry = registry
        self._model_config = model_config
        self._policy = policy
        self._model_service = model_service
        self._agent_service = agent_service
        self.profiles = ModelProfileRegistry(workspace_root / "config" / "model-profiles")
        self.router = ModelRouter(policy, self.profiles)
        self.context_engine = ContextEngine(
            session_factory,
            registry,
            policy,
            workspace_root=workspace_root,
            system_prompt=system_prompt or load_system_prompt(),
            knowledge_service=knowledge_service,
            memory_service=memory_service,
            research_service=research_service,
            preference_service=preference_service,
        )

    async def route(self, request: RoutingRequest) -> RoutingDecision:
        hardware = cached_hardware_report()
        agent = await self._resolve_agent(request.agent_id)
        providers = await self._model_service.providers()
        models = await self._model_service.list_models(hardware)
        manual = request
        if request.manual_provider is None and request.manual_model is None:
            manual = request.model_copy(
                update={
                    "manual_provider": None,
                    "manual_model": None,
                }
            )
        return self.router.route(
            manual,
            models=models,
            providers=providers,
            hardware=hardware,
            agent=agent,
        )

    async def context_preview(
        self,
        *,
        conversation_id: str,
        user_id: str,
        assistant_message_id: str,
        message: str,
        provider: str,
        model: str,
        settings: GenerationSettings,
        agent_id: str | None,
    ) -> PreparedContext:
        agent = await self._resolve_agent(agent_id)
        return await self.context_engine.build(
            conversation_id=conversation_id,
            user_id=user_id,
            assistant_message_id=assistant_message_id,
            current_user_message=message,
            provider_id=provider,
            model_id=model,
            settings=settings,
            agent=agent,
        )

    async def _resolve_agent(self, agent_id: str | None) -> AgentDefinition | None:
        return await self._agent_service.resolve(agent_id)

    def defaults(self) -> dict[str, str | None]:
        return {
            "provider": self._model_config.default_provider,
            "model": self._model_config.default_model,
        }
