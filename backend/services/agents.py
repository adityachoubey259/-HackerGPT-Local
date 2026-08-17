"""Agent application service."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.agents.models import AgentCreate, AgentDefinition, AgentPatch
from backend.agents.registry import AgentRegistry, AgentRegistryError
from backend.api.errors import ApplicationError
from backend.db.models import CustomAgent
from backend.db.repositories.sqlalchemy import SqlAlchemyAgentRepository, SqlAlchemyUserRepository


class AgentService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        registry: AgentRegistry,
    ) -> None:
        self._session_factory = session_factory
        self._registry = registry

    async def list_agents(self) -> list[AgentDefinition]:
        async with self._session_factory() as session:
            user = await SqlAlchemyUserRepository(session).get_or_create_local()
            custom = await SqlAlchemyAgentRepository(session).list_for_user(user.id)
        return [
            *self._registry.list(include_disabled=True),
            *[custom_to_definition(row) for row in custom],
        ]

    async def get_agent(self, agent_id: str) -> AgentDefinition:
        builtin = self._get_builtin(agent_id)
        if builtin is not None:
            return builtin
        async with self._session_factory() as session:
            user = await SqlAlchemyUserRepository(session).get_or_create_local()
            custom = await SqlAlchemyAgentRepository(session).get(user.id, agent_id)
        if custom is None:
            raise ApplicationError("AGENT_NOT_FOUND", "Agent was not found.", status_code=404)
        return custom_to_definition(custom)

    async def resolve(self, agent_id: str | None) -> AgentDefinition:
        if not agent_id:
            return self._registry.default()
        return await self.get_agent(agent_id)

    async def create(self, request: AgentCreate) -> AgentDefinition:
        slug = request.id or slugify(request.name)
        config = dict(request.configuration)
        async with self._session_factory() as session:
            user = await SqlAlchemyUserRepository(session).get_or_create_local()
            try:
                custom = await SqlAlchemyAgentRepository(session).create(
                    user_id=user.id,
                    slug=slug,
                    name=request.name,
                    description=request.description,
                    system_prompt=request.system_prompt,
                    configuration=config,
                    enabled=request.enabled,
                )
                await session.commit()
            except IntegrityError as exc:
                await session.rollback()
                raise ApplicationError(
                    "AGENT_DUPLICATE",
                    "A custom agent with this ID already exists.",
                    status_code=409,
                ) from exc
        return custom_to_definition(custom)

    async def patch(self, agent_id: str, request: AgentPatch) -> AgentDefinition:
        if self._get_builtin(agent_id) is not None:
            raise ApplicationError(
                "BUILT_IN_AGENT_IMMUTABLE",
                "Built-in agents cannot be edited through the API.",
                status_code=409,
            )
        async with self._session_factory() as session:
            user = await SqlAlchemyUserRepository(session).get_or_create_local()
            repo = SqlAlchemyAgentRepository(session)
            custom = await repo.get(user.id, agent_id)
            if custom is None:
                raise ApplicationError("AGENT_NOT_FOUND", "Agent was not found.", status_code=404)
            updates = request.model_dump(exclude_unset=True)
            custom = await repo.update(custom, **updates)
            await session.commit()
        return custom_to_definition(custom)

    async def delete(self, agent_id: str) -> None:
        if self._get_builtin(agent_id) is not None:
            raise ApplicationError(
                "BUILT_IN_AGENT_IMMUTABLE",
                "Built-in agents cannot be deleted.",
                status_code=409,
            )
        async with self._session_factory() as session:
            user = await SqlAlchemyUserRepository(session).get_or_create_local()
            repo = SqlAlchemyAgentRepository(session)
            custom = await repo.get(user.id, agent_id)
            if custom is None:
                raise ApplicationError("AGENT_NOT_FOUND", "Agent was not found.", status_code=404)
            await repo.delete(custom)
            await session.commit()

    async def duplicate(self, agent_id: str) -> AgentDefinition:
        source = await self.get_agent(agent_id)
        return await self.create(
            AgentCreate(
                id=unique_duplicate_slug(source.id),
                name=f"{source.name} Copy",
                description=source.description,
                system_prompt=source.system_prompt,
                configuration=source.model_dump(
                    exclude={"id", "name", "description", "system_prompt", "built_in"}
                ),
                enabled=True,
            )
        )

    def _get_builtin(self, agent_id: str) -> AgentDefinition | None:
        try:
            return self._registry.get(agent_id)
        except AgentRegistryError:
            return None


def custom_to_definition(row: CustomAgent) -> AgentDefinition:
    config: dict[str, Any] = dict(row.configuration)
    return AgentDefinition.model_validate(
        config
        | {
            "id": row.slug,
            "name": row.name,
            "description": row.description,
            "system_prompt": row.system_prompt,
            "enabled": row.enabled,
            "built_in": False,
            "metadata": config.get("metadata", {}) | {"custom_id": row.id},
        }
    )


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9._-]+", "-", value.lower()).strip("-._")
    return slug or "custom-agent"


def unique_duplicate_slug(value: str) -> str:
    return f"{value}-copy"
