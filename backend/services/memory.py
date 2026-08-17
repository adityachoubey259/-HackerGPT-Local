"""Long-term memory application service."""

from __future__ import annotations

import re
from collections import Counter

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.api.errors import ApplicationError
from backend.api.schemas.memory import (
    MemoryCreateRequest,
    MemoryExportResponse,
    MemoryListResponse,
    MemoryPatchRequest,
    MemoryRead,
    MemoryScope,
    MemorySearchRequest,
    MemorySearchResponse,
    MemorySearchResult,
    MemoryType,
)
from backend.core.policy import PolicyConfig
from backend.core.time import utc_now
from backend.db.models import Memory
from backend.db.repositories.sqlalchemy import SqlAlchemyMemoryRepository, SqlAlchemyUserRepository
from backend.memory.models import MemoryContextItem
from backend.rag.checksums import sha256_text
from backend.rag.text import estimate_tokens


class MemoryService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        policy: PolicyConfig,
    ) -> None:
        self._session_factory = session_factory
        self._policy = policy

    async def list_memories(
        self,
        *,
        limit: int,
        offset: int,
        search: str | None,
        memory_type: str | None,
        enabled: bool | None,
    ) -> MemoryListResponse:
        async with self._session_factory() as session:
            user = await SqlAlchemyUserRepository(session).get_or_create_local()
            items, total = await SqlAlchemyMemoryRepository(session).list_memories(
                user.id,
                limit=limit,
                offset=offset,
                search=search,
                memory_type=memory_type,
                enabled=enabled,
            )
        return MemoryListResponse(items=[memory_to_read(item) for item in items], total=total)

    async def create(self, request: MemoryCreateRequest) -> MemoryRead:
        self._ensure_enabled()
        async with self._session_factory() as session:
            user = await SqlAlchemyUserRepository(session).get_or_create_local()
            memory = await SqlAlchemyMemoryRepository(session).create(
                user_id=user.id,
                memory_type=request.memory_type.value,
                scope=request.scope.value,
                title=request.title,
                content=request.content,
                checksum=sha256_text(request.content),
                project_id=request.project_id,
                conversation_id=request.conversation_id,
                source="manual" if request.source_message_id is None else "chat_action",
                source_message_id=request.source_message_id,
                importance=request.importance,
                pinned=request.pinned,
                enabled=request.enabled,
                expires_at=request.expires_at,
                tags=request.tags,
                metadata={"user_confirmed": True},
            )
            await session.commit()
        return memory_to_read(memory)

    async def get(self, memory_id: str) -> MemoryRead:
        async with self._session_factory() as session:
            memory = await self._get_scoped(session, memory_id)
        return memory_to_read(memory)

    async def patch(self, memory_id: str, request: MemoryPatchRequest) -> MemoryRead:
        async with self._session_factory() as session:
            repo = SqlAlchemyMemoryRepository(session)
            memory = await self._get_scoped(session, memory_id)
            updates = request.model_dump(exclude_unset=True)
            if "content" in updates and updates["content"] is not None:
                updates["checksum"] = sha256_text(updates["content"])
            memory = await repo.update(memory, **updates)
            await session.commit()
        return memory_to_read(memory)

    async def delete(self, memory_id: str) -> None:
        async with self._session_factory() as session:
            repo = SqlAlchemyMemoryRepository(session)
            memory = await self._get_scoped(session, memory_id)
            await repo.delete(memory)
            await session.commit()

    async def search(self, request: MemorySearchRequest) -> MemorySearchResponse:
        async with self._session_factory() as session:
            user = await SqlAlchemyUserRepository(session).get_or_create_local()
            memories = await SqlAlchemyMemoryRepository(session).active_for_user(user.id)
        scored = [
            MemorySearchResult(
                memory=memory_to_read(memory), relevance=score_memory(request.query, memory)
            )
            for memory in memories
            if request.memory_type is None or memory.memory_type == request.memory_type.value
        ]
        selected = sorted(scored, key=lambda item: item.relevance, reverse=True)[: request.limit]
        return MemorySearchResponse(
            items=selected,
            diagnostics={"candidate_count": len(memories), "selected_memories": len(selected)},
        )

    async def export(self) -> MemoryExportResponse:
        async with self._session_factory() as session:
            user = await SqlAlchemyUserRepository(session).get_or_create_local()
            items, _ = await SqlAlchemyMemoryRepository(session).list_memories(
                user.id,
                limit=500,
                offset=0,
                enabled=None,
            )
        return MemoryExportResponse(
            exported_at=utc_now(), items=[memory_to_read(item) for item in items]
        )

    async def stats(self) -> dict[str, object]:
        async with self._session_factory() as session:
            user = await SqlAlchemyUserRepository(session).get_or_create_local()
            count = await SqlAlchemyMemoryRepository(session).stats(user.id)
        return {
            "enabled": self._policy.memory_policy.long_term_memory_enabled,
            "memory_count": count,
            "semantic_store_status": "local",
        }

    async def context_for_query(
        self, user_id: str, query: str, *, budget_tokens: int
    ) -> list[MemoryContextItem]:
        if not self._policy.memory_policy.long_term_memory_enabled:
            return []
        async with self._session_factory() as session:
            memories = await SqlAlchemyMemoryRepository(session).active_for_user(user_id)
        scored = sorted(
            ((memory, score_memory(query, memory)) for memory in memories),
            key=lambda item: (item[0].pinned, item[1], item[0].importance),
            reverse=True,
        )
        selected: list[MemoryContextItem] = []
        used = 0
        for index, (memory, relevance) in enumerate(scored, start=1):
            if relevance <= 0 and not memory.pinned:
                continue
            text = memory.summary or memory.content
            cost = estimate_tokens(text)
            if used + cost > budget_tokens:
                continue
            used += cost
            selected.append(
                MemoryContextItem(
                    memory_id=memory.id,
                    citation_id=f"[M{index}]",
                    title=memory.title,
                    content=text,
                    memory_type=memory.memory_type,
                    scope=memory.scope,
                    relevance=relevance,
                )
            )
            if len(selected) >= self._policy.memory_policy.maximum_retrieved_memories:
                break
        return selected

    def _ensure_enabled(self) -> None:
        if not self._policy.memory_policy.local_storage_enabled:
            raise ApplicationError(
                "MEMORY_DISABLED",
                "Local memory storage is disabled.",
                status_code=403,
            )

    async def _get_scoped(self, session: AsyncSession, memory_id: str) -> Memory:
        user = await SqlAlchemyUserRepository(session).get_or_create_local()
        memory = await SqlAlchemyMemoryRepository(session).get(memory_id, user.id)
        if memory is None:
            raise ApplicationError("MEMORY_NOT_FOUND", "Memory was not found.", status_code=404)
        return memory


def score_memory(query: str, memory: Memory) -> float:
    if memory.expires_at is not None and memory.expires_at <= utc_now():
        return 0.0
    query_terms = Counter(tokens(query))
    if not query_terms:
        return 0.0
    haystack = f"{memory.title}\n{memory.content}\n{' '.join(memory.tags)}"
    memory_terms = Counter(tokens(haystack))
    overlap = sum(min(count, memory_terms.get(term, 0)) for term, count in query_terms.items())
    lexical = overlap / sum(query_terms.values())
    bonus = 0.12 if memory.pinned else 0.0
    importance = memory.importance / 100
    return round(min(1.0, lexical + bonus + importance), 8)


def tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_]{2,}", text.lower())


def memory_to_read(memory: Memory) -> MemoryRead:
    return MemoryRead(
        id=memory.id,
        memory_type=MemoryType(memory.memory_type),
        scope=MemoryScope(memory.scope),
        project_id=memory.project_id,
        conversation_id=memory.conversation_id,
        title=memory.title,
        content=memory.content,
        summary=memory.summary,
        source=memory.source,
        source_message_id=memory.source_message_id,
        importance=memory.importance,
        pinned=memory.pinned,
        enabled=memory.enabled,
        tags=memory.tags,
        metadata=memory.metadata_json,
        last_used_at=memory.last_used_at,
        expires_at=memory.expires_at,
        created_at=memory.created_at,
        updated_at=memory.updated_at,
    )
