"""Agent registry and secure tool framework.

Revision ID: 0004_agents_tools
Revises: 0003_rag_memory
Create Date: 2026-08-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_agents_tools"
down_revision: str | None = "0003_rag_memory"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("conversations", sa.Column("agent_id", sa.String(length=120), nullable=True))
    op.create_index("ix_conversations_agent_id", "conversations", ["agent_id"])

    op.create_table(
        "custom_agents",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("configuration", sa.JSON(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("built_in_origin", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_custom_agents_user_slug", "custom_agents", ["user_id", "slug"], unique=True)
    op.create_index("ix_custom_agents_user_enabled", "custom_agents", ["user_id", "enabled"])

    op.create_table(
        "tool_executions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("conversation_id", sa.String(), nullable=True),
        sa.Column("message_id", sa.String(), nullable=True),
        sa.Column("agent_id", sa.String(length=120), nullable=True),
        sa.Column("request_id", sa.String(length=120), nullable=True),
        sa.Column("generation_id", sa.String(length=80), nullable=True),
        sa.Column("tool_name", sa.String(length=120), nullable=False),
        sa.Column("permission_class", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("input", sa.JSON(), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("working_directory", sa.Text(), nullable=True),
        sa.Column("command_display", sa.Text(), nullable=True),
        sa.Column("stdout", sa.Text(), nullable=True),
        sa.Column("stderr", sa.Text(), nullable=True),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("truncated", sa.Boolean(), nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tool_exec_user_status", "tool_executions", ["user_id", "status"])
    op.create_index(
        "ix_tool_exec_user_tool_created",
        "tool_executions",
        ["user_id", "tool_name", "created_at"],
    )
    op.create_index("ix_tool_exec_agent", "tool_executions", ["agent_id"])
    op.create_index("ix_tool_exec_input_hash", "tool_executions", ["input_hash"])

    op.create_table(
        "tool_confirmations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("execution_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("tool_name", sa.String(length=120), nullable=False),
        sa.Column("permission_class", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("risk_summary", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["execution_id"], ["tool_executions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tool_confirmations_execution", "tool_confirmations", ["execution_id"])
    op.create_index(
        "ix_tool_confirmations_user_status",
        "tool_confirmations",
        ["user_id", "status"],
    )
    op.create_index("ix_tool_confirmations_expires", "tool_confirmations", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_tool_confirmations_expires", table_name="tool_confirmations")
    op.drop_index("ix_tool_confirmations_user_status", table_name="tool_confirmations")
    op.drop_index("ix_tool_confirmations_execution", table_name="tool_confirmations")
    op.drop_table("tool_confirmations")
    op.drop_index("ix_tool_exec_input_hash", table_name="tool_executions")
    op.drop_index("ix_tool_exec_agent", table_name="tool_executions")
    op.drop_index("ix_tool_exec_user_tool_created", table_name="tool_executions")
    op.drop_index("ix_tool_exec_user_status", table_name="tool_executions")
    op.drop_table("tool_executions")
    op.drop_index("ix_custom_agents_user_enabled", table_name="custom_agents")
    op.drop_index("uq_custom_agents_user_slug", table_name="custom_agents")
    op.drop_table("custom_agents")
    op.drop_index("ix_conversations_agent_id", table_name="conversations")
    op.drop_column("conversations", "agent_id")
