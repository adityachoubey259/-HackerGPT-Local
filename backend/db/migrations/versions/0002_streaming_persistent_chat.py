"""Streaming chat and persistent conversation metadata.

Revision ID: 0002_streaming_persistent_chat
Revises: 0001_initial_schema
Create Date: 2026-08-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_streaming_persistent_chat"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("client_request_id", sa.String(length=120), nullable=True))
    op.add_column("messages", sa.Column("generation_id", sa.String(length=64), nullable=True))
    op.add_column("messages", sa.Column("generation_status", sa.String(length=32), nullable=True))
    op.add_column("messages", sa.Column("provider", sa.String(length=80), nullable=True))
    op.add_column("messages", sa.Column("model", sa.String(length=240), nullable=True))
    op.add_column("messages", sa.Column("finish_reason", sa.String(length=80), nullable=True))
    op.add_column("messages", sa.Column("prompt_tokens", sa.Integer(), nullable=True))
    op.add_column("messages", sa.Column("completion_tokens", sa.Integer(), nullable=True))
    op.add_column("messages", sa.Column("total_tokens", sa.Integer(), nullable=True))
    op.add_column("messages", sa.Column("time_to_first_token_ms", sa.Float(), nullable=True))
    op.add_column("messages", sa.Column("duration_ms", sa.Float(), nullable=True))
    op.add_column("messages", sa.Column("tokens_per_second", sa.Float(), nullable=True))
    op.add_column("messages", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))

    op.execute("UPDATE messages SET updated_at = created_at")

    with op.batch_alter_table("messages") as batch_op:
        batch_op.alter_column("updated_at", nullable=False)

    op.create_index(
        "ix_conversations_user_archived_updated",
        "conversations",
        ["user_id", "archived", "updated_at"],
    )
    op.create_index("ix_conversations_user_updated", "conversations", ["user_id", "updated_at"])
    op.create_index(
        "ix_messages_conversation_created",
        "messages",
        ["conversation_id", "created_at"],
    )
    op.create_index(op.f("ix_messages_generation_status"), "messages", ["generation_status"])
    op.create_index("uq_messages_client_request_id", "messages", ["client_request_id"], unique=True)
    op.create_index("uq_messages_generation_id", "messages", ["generation_id"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_messages_generation_id", table_name="messages")
    op.drop_index("uq_messages_client_request_id", table_name="messages")
    op.drop_index(op.f("ix_messages_generation_status"), table_name="messages")
    op.drop_index("ix_messages_conversation_created", table_name="messages")
    op.drop_index("ix_conversations_user_updated", table_name="conversations")
    op.drop_index("ix_conversations_user_archived_updated", table_name="conversations")

    op.drop_column("messages", "updated_at")
    op.drop_column("messages", "tokens_per_second")
    op.drop_column("messages", "duration_ms")
    op.drop_column("messages", "time_to_first_token_ms")
    op.drop_column("messages", "total_tokens")
    op.drop_column("messages", "completion_tokens")
    op.drop_column("messages", "prompt_tokens")
    op.drop_column("messages", "finish_reason")
    op.drop_column("messages", "model")
    op.drop_column("messages", "provider")
    op.drop_column("messages", "generation_status")
    op.drop_column("messages", "generation_id")
    op.drop_column("messages", "client_request_id")
