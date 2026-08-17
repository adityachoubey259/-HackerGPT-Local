from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.db.models import User
from backend.db.repositories.sqlalchemy import (
    SqlAlchemyConversationRepository,
    SqlAlchemyMessageRepository,
    SqlAlchemySettingRepository,
    SqlAlchemyUserRepository,
)
from backend.db.session import session_scope


async def test_repositories_create_initial_models(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        users = SqlAlchemyUserRepository(session)
        conversations = SqlAlchemyConversationRepository(session)
        messages = SqlAlchemyMessageRepository(session)
        settings = SqlAlchemySettingRepository(session)

        user = await users.create("Local User")
        conversation = await conversations.create(user.id, "First conversation")
        message = await messages.create(
            conversation.id,
            "user",
            "hello",
            metadata={"source": "test"},
        )
        setting = await settings.set("theme", {"value": "system"})
        await session.commit()

    async with session_factory() as session:
        assert await SqlAlchemyUserRepository(session).get(user.id) is not None
        assert await SqlAlchemyConversationRepository(session).get(conversation.id) is not None
        stored_setting = await SqlAlchemySettingRepository(session).get(setting.key)
        assert stored_setting is not None
        assert stored_setting.value == {"value": "system"}
        stored_message = await session.get(type(message), message.id)
        assert stored_message is not None
        assert stored_message.metadata_json == {"source": "test"}


async def test_session_scope_rolls_back_on_failure(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    with pytest.raises(RuntimeError):
        async for session in session_scope(session_factory):
            await SqlAlchemyUserRepository(session).create("Rollback User")
            raise RuntimeError("force rollback")

    async with session_factory() as session:
        result = await session.execute(select(User).where(User.display_name == "Rollback User"))
        assert result.scalar_one_or_none() is None
