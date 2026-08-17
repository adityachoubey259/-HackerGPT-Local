"""Shared FastAPI dependencies."""

from collections.abc import AsyncIterator
from typing import cast

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.core.config import AppSettings
from backend.core.policy import PolicyConfig
from backend.db.session import session_scope


def get_app_settings(request: Request) -> AppSettings:
    return cast(AppSettings, request.app.state.settings)


def get_policy(request: Request) -> PolicyConfig:
    return cast(PolicyConfig, request.app.state.policy)


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async for session in session_scope(session_factory):
        yield session
