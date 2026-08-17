from __future__ import annotations

import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config


def test_initial_migration_applies_to_empty_database(tmp_path: Path) -> None:
    db_path = tmp_path / "migration.db"
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_path}")

    command.upgrade(cfg, "head")

    with sqlite3.connect(db_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        user_columns = {row[1] for row in connection.execute("PRAGMA table_info(users)").fetchall()}
    assert {"alembic_version", "users", "conversations", "messages", "settings"} <= tables
    assert {"username", "password_hash", "role", "is_bootstrap", "auth_metadata"} <= user_columns
