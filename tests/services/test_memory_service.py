from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.api.schemas.memory import MemoryCreateRequest, MemorySearchRequest
from backend.core.policy import PolicyConfig
from backend.db.repositories.sqlalchemy import SqlAlchemyUserRepository
from backend.services.memory import MemoryService


@pytest.mark.asyncio
async def test_memory_service_requires_explicit_create_and_retrieves_context(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    service = MemoryService(session_factory, PolicyConfig())
    created = await service.create(
        MemoryCreateRequest(
            title="Local runtime preference",
            content="Prefer Ollama for quick local coding tasks.",
            importance=5,
            pinned=True,
            tags=["runtime"],
        )
    )

    listed = await service.list_memories(
        limit=10,
        offset=0,
        search="ollama",
        memory_type=None,
        enabled=True,
    )
    searched = await service.search(MemorySearchRequest(query="Which runtime for coding?"))
    exported = await service.export()
    async with session_factory() as session:
        user = await SqlAlchemyUserRepository(session).get_or_create_local()
    context = await service.context_for_query(user.id, "coding runtime", budget_tokens=100)

    assert listed.total == 1
    assert listed.items[0].id == created.id
    assert searched.items[0].memory.title == "Local runtime preference"
    assert exported.items[0].metadata["user_confirmed"] is True
    assert context[0].citation_id == "[M1]"
    assert "Ollama" in context[0].content
