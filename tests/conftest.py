from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from backend.core.config import AppSettings, AuthSettings, DatabaseSettings
from backend.db.base import Base
from backend.db.session import create_engine, create_session_factory


@pytest.fixture
def temp_db_url(tmp_path: Path) -> str:
    return f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"


@pytest.fixture
def test_settings(temp_db_url: str, tmp_path: Path) -> AppSettings:
    return AppSettings(
        environment="test",
        debug=True,
        auth=AuthSettings(enabled=False),
        database=DatabaseSettings(url=temp_db_url),
        paths={
            "data_dir": tmp_path,
            "databases_dir": tmp_path,
            "uploads_dir": tmp_path / "uploads",
            "knowledge_dir": tmp_path / "knowledge",
            "models_dir": tmp_path / "models",
        },
    )


@pytest.fixture
async def db_engine(test_settings: AppSettings) -> AsyncIterator[AsyncEngine]:
    engine = create_engine(test_settings.database)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
def session_factory(db_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return create_session_factory(db_engine)


@pytest.fixture(autouse=True)
def clean_hackergpt_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for key in list(__import__("os").environ):
        if key.startswith("HACKERGPT_"):
            monkeypatch.delenv(key, raising=False)
    yield
