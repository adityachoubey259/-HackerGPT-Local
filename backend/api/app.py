"""FastAPI application factory."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect

from backend.agents import AgentRegistry
from backend.api.errors import register_error_handlers
from backend.api.middleware.auth import AuthMiddleware
from backend.api.middleware.metrics import LocalMetricsMiddleware
from backend.api.middleware.request_context import (
    RequestContextMiddleware,
    RequestIdResponseHeaderMiddleware,
)
from backend.api.middleware.security_headers import SecurityHeadersMiddleware
from backend.api.routes import create_v1_router
from backend.auth import AuthService
from backend.core.config import AppSettings, load_settings
from backend.core.logging import configure_logging
from backend.core.policy import PolicyConfig, load_policy
from backend.core.version import APP_VERSION
from backend.db.repositories.sqlalchemy import SqlAlchemyMessageRepository
from backend.db.session import create_engine, create_session_factory
from backend.llm.config import load_model_provider_config
from backend.llm.providers.factory import build_provider_registry
from backend.rag.embeddings import EmbeddingProviderRegistry
from backend.rag.vectorstores import VectorStoreRegistry
from backend.services.agents import AgentService
from backend.services.chat import ChatService
from backend.services.evaluation import EvaluationService
from backend.services.generation_manager import GenerationManager
from backend.services.health import HealthService
from backend.services.intelligence import IntelligenceService
from backend.services.knowledge import KnowledgeService
from backend.services.learning import LearningService
from backend.services.memory import MemoryService
from backend.services.models import ModelService, ModelSuitabilityService
from backend.services.observability import LocalMetrics, ObservabilityService
from backend.services.preferences import PreferenceService
from backend.services.prompt_architect import PromptArchitectService
from backend.services.prompts import load_system_prompt
from backend.services.research import ResearchService
from backend.services.security_workspace import SecurityWorkspaceService
from backend.services.tools import ToolService
from backend.tools import ToolRegistry, build_builtin_tools


def create_app(settings: AppSettings | None = None) -> FastAPI:
    resolved_settings = settings or load_settings()
    workspace_root = Path(__file__).resolve().parents[2]
    configure_logging(resolved_settings.logging)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        policy: PolicyConfig = load_policy()
        model_config = load_model_provider_config()
        registry = build_provider_registry(model_config, policy)
        engine = create_engine(resolved_settings.database)
        app.state.engine = engine
        app.state.session_factory = create_session_factory(engine)
        async with engine.connect() as connection:
            has_messages_table = await connection.run_sync(
                lambda sync_connection: inspect(sync_connection).has_table("messages")
            )
        if has_messages_table:
            async with app.state.session_factory() as session:
                await SqlAlchemyMessageRepository(session).mark_incomplete_generations_interrupted()
                await session.commit()
        app.state.settings = resolved_settings
        app.state.policy = policy
        app.state.auth_service = AuthService(
            app.state.session_factory,
            resolved_settings.auth,
            data_dir=resolved_settings.paths.data_dir,
        )
        await app.state.auth_service.bootstrap_admin()
        app.state.local_metrics = LocalMetrics()
        app.state.model_config = model_config
        app.state.model_registry = registry
        app.state.model_service = ModelService(registry, model_config, ModelSuitabilityService())
        app.state.tool_registry = ToolRegistry(build_builtin_tools(policy, workspace_root))
        app.state.agent_registry = AgentRegistry(
            policy=policy,
            known_tools=app.state.tool_registry.names(),
        )
        app.state.agent_service = AgentService(
            app.state.session_factory,
            app.state.agent_registry,
        )
        app.state.tool_service = ToolService(
            app.state.session_factory,
            policy,
            app.state.tool_registry,
            app.state.agent_service,
            workspace_root=workspace_root,
        )
        app.state.embedding_registry = EmbeddingProviderRegistry()
        app.state.vector_store_registry = VectorStoreRegistry()
        app.state.memory_service = MemoryService(app.state.session_factory, policy)
        app.state.knowledge_service = KnowledgeService(
            app.state.session_factory,
            resolved_settings,
            policy,
            app.state.embedding_registry,
            app.state.vector_store_registry,
        )
        app.state.security_workspace_service = SecurityWorkspaceService(
            app.state.session_factory,
            policy,
            workspace_root=workspace_root,
        )
        app.state.research_service = ResearchService(app.state.session_factory, policy)
        app.state.preference_service = PreferenceService(app.state.session_factory, policy)
        app.state.intelligence_service = IntelligenceService(
            app.state.session_factory,
            registry,
            model_config,
            policy,
            app.state.model_service,
            app.state.agent_service,
            workspace_root=workspace_root,
            knowledge_service=app.state.knowledge_service,
            memory_service=app.state.memory_service,
            research_service=app.state.research_service,
            preference_service=app.state.preference_service,
            system_prompt=load_system_prompt(),
        )
        app.state.prompt_architect_service = PromptArchitectService(
            policy,
            workspace_root=workspace_root,
        )
        app.state.evaluation_service = EvaluationService(
            workspace_root=workspace_root,
            data_dir=resolved_settings.paths.data_dir,
        )
        app.state.learning_service = LearningService(
            data_dir=resolved_settings.paths.data_dir,
            workspace_root=workspace_root,
        )
        app.state.generation_manager = GenerationManager()
        app.state.chat_service = ChatService(
            app.state.session_factory,
            registry,
            {
                "provider": model_config.default_provider,
                "model": model_config.default_model,
            },
            app.state.generation_manager,
            load_system_prompt(),
            knowledge_service=app.state.knowledge_service,
            memory_service=app.state.memory_service,
            agent_service=app.state.agent_service,
            intelligence_service=app.state.intelligence_service,
            preference_service=app.state.preference_service,
            policy=policy,
        )
        app.state.started_at_monotonic = time.monotonic()
        app.state.health_service = HealthService(
            resolved_settings,
            startup_monotonic=app.state.started_at_monotonic,
        )
        app.state.observability_service = ObservabilityService(
            resolved_settings,
            app.state.local_metrics,
            workspace_root=workspace_root,
            startup_monotonic=app.state.started_at_monotonic,
        )
        try:
            yield
        finally:
            await engine.dispose()

    app = FastAPI(
        title="HackerGPT Local API",
        version=APP_VERSION,
        debug=resolved_settings.debug,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.api.allowed_origins,
        allow_credentials=resolved_settings.api.allow_credentials,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(LocalMetricsMiddleware)
    app.add_middleware(AuthMiddleware)
    app.add_middleware(RequestIdResponseHeaderMiddleware)
    app.add_middleware(RequestContextMiddleware)
    register_error_handlers(app)
    app.include_router(create_v1_router())
    _register_frontend_routes(app, workspace_root, resolved_settings)
    return app


def _register_frontend_routes(
    app: FastAPI,
    workspace_root: Path,
    settings: AppSettings,
) -> None:
    if not settings.frontend.serve_static or settings.environment == "test":
        return
    dist_dir = settings.frontend.dist_dir
    if not dist_dir.is_absolute():
        dist_dir = workspace_root / dist_dir
    assets_dir = dist_dir / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    @app.get("/{path:path}", include_in_schema=False, response_model=None)
    async def spa_fallback(path: str) -> FileResponse | HTMLResponse:
        if path.startswith("api/"):
            return HTMLResponse("Not found", status_code=404)
        index = dist_dir / "index.html"
        if index.is_file():
            return FileResponse(index)
        return HTMLResponse(
            "<!doctype html><title>HackerGPT Local</title>"
            "<h1>Frontend build unavailable</h1>"
            "<p>Run <code>cd frontend && npm.cmd run build</code> for production-local UI.</p>",
            status_code=503,
        )
