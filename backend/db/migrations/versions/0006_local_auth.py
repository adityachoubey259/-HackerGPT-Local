"""Add local authentication fields.

Revision ID: 0006_local_auth
Revises: 0005_security_research
Create Date: 2026-08-11
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_local_auth"
down_revision: str | None = "0005_security_research"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(length=80), nullable=True))
    op.add_column("users", sa.Column("password_hash", sa.String(length=300), nullable=True))
    op.add_column(
        "users",
        sa.Column("role", sa.String(length=40), server_default="user", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("is_bootstrap", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("auth_metadata", sa.JSON(), server_default="{}", nullable=False),
    )
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_column("users", "auth_metadata")
    op.drop_column("users", "is_bootstrap")
    op.drop_column("users", "role")
    op.drop_column("users", "password_hash")
    op.drop_column("users", "username")
