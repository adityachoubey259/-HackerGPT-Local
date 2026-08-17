"""Async database engine and session lifecycle."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.core.config import DatabaseSettings


def _ensure_sqlite_parent(url: str) -> None:
    if not url.startswith("sqlite+aiosqlite:///"):
        return
    path_text = url.removeprefix("sqlite+aiosqlite:///")
    if path_text == ":memory:" or path_text.startswith("file:"):
        return
    Path(path_text).parent.mkdir(parents=True, exist_ok=True)


def create_engine(settings: DatabaseSettings) -> AsyncEngine:
    _ensure_sqlite_parent(settings.url)
    return create_async_engine(settings.url, echo=settings.echo, future=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


async def session_scope(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
