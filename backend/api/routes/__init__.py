"""Versioned API route registration."""

from fastapi import APIRouter

from backend.api.routes import (
    agents,
    auth,
    chat,
    config,
    conversations,
    diagnostics,
    evaluations,
    health,
    intelligence,
    knowledge,
    learning,
    memory,
    models,
    preferences,
    prompts,
    research,
    security,
    system,
    tools,
)

API_V1_PREFIX = "/api/v1"


def create_v1_router() -> APIRouter:
    router = APIRouter(prefix=API_V1_PREFIX)
    router.include_router(health.router)
    router.include_router(auth.router)
    router.include_router(system.router)
    router.include_router(config.router)
    router.include_router(diagnostics.router)
    router.include_router(models.router)
    router.include_router(intelligence.router)
    router.include_router(preferences.router)
    router.include_router(prompts.router)
    router.include_router(evaluations.router)
    router.include_router(learning.router)
    router.include_router(conversations.router)
    router.include_router(agents.router)
    router.include_router(chat.router)
    router.include_router(knowledge.router)
    router.include_router(memory.router)
    router.include_router(tools.router)
    router.include_router(security.router)
    router.include_router(research.router)
    return router
