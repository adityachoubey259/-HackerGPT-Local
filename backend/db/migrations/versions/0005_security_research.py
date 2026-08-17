"""security and research workspace tables

Revision ID: 0005_security_research
Revises: 0004_agents_tools
Create Date: 2026-08-10 20:30:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005_security_research"
down_revision = "0004_agents_tools"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "security_workspaces",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("mode", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("active_scope_id", sa.String(length=36), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_security_workspaces_user_name"),
    )
    op.create_index("ix_security_workspaces_user_id", "security_workspaces", ["user_id"])
    op.create_index("ix_security_workspaces_mode", "security_workspaces", ["mode"])
    op.create_index("ix_security_workspaces_enabled", "security_workspaces", ["enabled"])

    op.create_table(
        "security_scopes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("scope_type", sa.String(length=80), nullable=False),
        sa.Column("target", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["security_workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "workspace_id", "name", name="uq_security_scopes_name"),
    )
    op.create_index("ix_security_scopes_user_id", "security_scopes", ["user_id"])
    op.create_index("ix_security_scopes_workspace_id", "security_scopes", ["workspace_id"])
    op.create_index("ix_security_scopes_scope_type", "security_scopes", ["scope_type"])
    op.create_index("ix_security_scopes_enabled", "security_scopes", ["enabled"])

    op.create_table(
        "security_findings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=True),
        sa.Column("scope_id", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.String(length=32), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=True),
        sa.Column("cwe", sa.String(length=40), nullable=True),
        sa.Column("cve", sa.String(length=40), nullable=True),
        sa.Column("affected_asset", sa.String(length=500), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False),
        sa.Column("remediation", sa.Text(), nullable=False),
        sa.Column("references", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["scope_id"], ["security_scopes.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["security_workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_security_findings_user_id", "security_findings", ["user_id"])
    op.create_index("ix_security_findings_workspace_id", "security_findings", ["workspace_id"])
    op.create_index("ix_security_findings_scope_id", "security_findings", ["scope_id"])
    op.create_index("ix_security_findings_severity", "security_findings", ["severity"])
    op.create_index("ix_security_findings_category", "security_findings", ["category"])
    op.create_index("ix_security_findings_cwe", "security_findings", ["cwe"])
    op.create_index("ix_security_findings_cve", "security_findings", ["cve"])

    op.create_table(
        "security_notes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=True),
        sa.Column("finding_id", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("references", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["finding_id"], ["security_findings.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["security_workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_security_notes_user_id", "security_notes", ["user_id"])
    op.create_index("ix_security_notes_workspace_id", "security_notes", ["workspace_id"])
    op.create_index("ix_security_notes_finding_id", "security_notes", ["finding_id"])

    op.create_table(
        "research_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=True),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("official_only", sa.Boolean(), nullable=False),
        sa.Column("filters", sa.JSON(), nullable=False),
        sa.Column("diagnostics", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_research_sessions_user_id", "research_sessions", ["user_id"])
    op.create_index("ix_research_sessions_status", "research_sessions", ["status"])

    op.create_table(
        "research_sources",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("citation_id", sa.String(length=40), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("normalized_url", sa.Text(), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("reliability", sa.String(length=80), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("content_checksum", sa.String(length=64), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["research_sessions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_research_sources_session_id", "research_sources", ["session_id"])
    op.create_index("ix_research_sources_user_id", "research_sources", ["user_id"])
    op.create_index("ix_research_sources_citation_id", "research_sources", ["citation_id"])
    op.create_index("ix_research_sources_normalized_url", "research_sources", ["normalized_url"])
    op.create_index("ix_research_sources_domain", "research_sources", ["domain"])

    op.create_table(
        "research_cache_entries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("normalized_url", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("normalized_url", name="uq_research_cache_normalized_url"),
    )
    op.create_index(
        "ix_research_cache_entries_normalized_url",
        "research_cache_entries",
        ["normalized_url"],
    )
    op.create_index("ix_research_cache_entries_domain", "research_cache_entries", ["domain"])
    op.create_index("ix_research_cache_entries_checksum", "research_cache_entries", ["checksum"])
    op.create_index(
        "ix_research_cache_entries_retrieved_at",
        "research_cache_entries",
        ["retrieved_at"],
    )
    op.create_index(
        "ix_research_cache_entries_expires_at",
        "research_cache_entries",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_research_cache_entries_expires_at", table_name="research_cache_entries")
    op.drop_index("ix_research_cache_entries_retrieved_at", table_name="research_cache_entries")
    op.drop_index("ix_research_cache_entries_checksum", table_name="research_cache_entries")
    op.drop_index("ix_research_cache_entries_domain", table_name="research_cache_entries")
    op.drop_index("ix_research_cache_entries_normalized_url", table_name="research_cache_entries")
    op.drop_table("research_cache_entries")
    op.drop_index("ix_research_sources_domain", table_name="research_sources")
    op.drop_index("ix_research_sources_normalized_url", table_name="research_sources")
    op.drop_index("ix_research_sources_citation_id", table_name="research_sources")
    op.drop_index("ix_research_sources_user_id", table_name="research_sources")
    op.drop_index("ix_research_sources_session_id", table_name="research_sources")
    op.drop_table("research_sources")
    op.drop_index("ix_research_sessions_status", table_name="research_sessions")
    op.drop_index("ix_research_sessions_user_id", table_name="research_sessions")
    op.drop_table("research_sessions")
    op.drop_index("ix_security_notes_finding_id", table_name="security_notes")
    op.drop_index("ix_security_notes_workspace_id", table_name="security_notes")
    op.drop_index("ix_security_notes_user_id", table_name="security_notes")
    op.drop_table("security_notes")
    op.drop_index("ix_security_findings_cve", table_name="security_findings")
    op.drop_index("ix_security_findings_cwe", table_name="security_findings")
    op.drop_index("ix_security_findings_category", table_name="security_findings")
    op.drop_index("ix_security_findings_severity", table_name="security_findings")
    op.drop_index("ix_security_findings_scope_id", table_name="security_findings")
    op.drop_index("ix_security_findings_workspace_id", table_name="security_findings")
    op.drop_index("ix_security_findings_user_id", table_name="security_findings")
    op.drop_table("security_findings")
    op.drop_index("ix_security_scopes_enabled", table_name="security_scopes")
    op.drop_index("ix_security_scopes_scope_type", table_name="security_scopes")
    op.drop_index("ix_security_scopes_workspace_id", table_name="security_scopes")
    op.drop_index("ix_security_scopes_user_id", table_name="security_scopes")
    op.drop_table("security_scopes")
    op.drop_index("ix_security_workspaces_enabled", table_name="security_workspaces")
    op.drop_index("ix_security_workspaces_mode", table_name="security_workspaces")
    op.drop_index("ix_security_workspaces_user_id", table_name="security_workspaces")
    op.drop_table("security_workspaces")
