"""Add workspace and coding tasks schema.

Revision ID: 0007_workspaces
Revises: 0006_local_auth
Create Date: 2026-08-18
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_workspaces"
down_revision: str | None = "0006_local_auth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("root_path", sa.Text(), nullable=False),
        sa.Column("trusted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("git_repository", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("git_branch", sa.String(length=255), nullable=True),
        sa.Column("language_summary", sa.String(length=255), nullable=True),
        sa.Column("framework_summary", sa.String(length=255), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("root_path"),
    )

    op.create_table(
        "coding_tasks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("user_request", sa.Text(), nullable=False),
        sa.Column("state", sa.String(length=50), nullable=False, server_default="queued"),
        sa.Column("mode", sa.String(length=50), nullable=False, server_default="agent"),
        sa.Column("model", sa.String(length=255), nullable=True),
        sa.Column("agent", sa.String(length=255), nullable=True),
        sa.Column("files_read", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("files_modified", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("commands_run", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("tests_run", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_coding_tasks_workspace_id"), "coding_tasks", ["workspace_id"])

    op.create_table(
        "workspace_changes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("old_hash", sa.String(length=64), nullable=True),
        sa.Column("new_hash", sa.String(length=64), nullable=True),
        sa.Column("patch_data", sa.Text(), nullable=True),
        sa.Column("old_content", sa.Text(), nullable=True),
        sa.Column("new_content", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["coding_tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workspace_changes_task_id"), "workspace_changes", ["task_id"])
    op.create_index(
        op.f("ix_workspace_changes_workspace_id"), "workspace_changes", ["workspace_id"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_workspace_changes_workspace_id"), table_name="workspace_changes")
    op.drop_index(op.f("ix_workspace_changes_task_id"), table_name="workspace_changes")
    op.drop_table("workspace_changes")
    op.drop_index(op.f("ix_coding_tasks_workspace_id"), table_name="coding_tasks")
    op.drop_table("coding_tasks")
    op.drop_table("workspaces")
