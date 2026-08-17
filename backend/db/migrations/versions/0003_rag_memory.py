"""RAG document ingestion and long-term memory.

Revision ID: 0003_rag_memory
Revises: 0002_streaming_persistent_chat
Create Date: 2026-08-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_rag_memory"
down_revision: str | None = "0002_streaming_persistent_chat"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("source_path", sa.Text(), nullable=True),
        sa.Column("mime_type", sa.String(length=180), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("parser", sa.String(length=80), nullable=True),
        sa.Column("title", sa.String(length=240), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("failure_code", sa.String(length=80), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_documents_user_status_updated", "documents", ["user_id", "status", "updated_at"]
    )
    op.create_index("ix_documents_checksum", "documents", ["checksum"])

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("citation_id", sa.String(length=40), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("section", sa.String(length=240), nullable=True),
        sa.Column("source_path", sa.Text(), nullable=True),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("character_count", sa.Integer(), nullable=False),
        sa.Column("embedding_provider", sa.String(length=80), nullable=True),
        sa.Column("embedding_model", sa.String(length=180), nullable=True),
        sa.Column("embedding_dimension", sa.Integer(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_document_chunks_document_index",
        "document_chunks",
        ["document_id", "chunk_index"],
        unique=True,
    )
    op.create_index("ix_document_chunks_user", "document_chunks", ["user_id"])
    op.create_index("ix_document_chunks_checksum", "document_chunks", ["checksum"])
    op.create_index("ix_document_chunks_citation", "document_chunks", ["citation_id"])

    op.create_table(
        "ingestion_jobs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("total_files", sa.Integer(), nullable=False),
        sa.Column("processed_files", sa.Integer(), nullable=False),
        sa.Column("chunks_indexed", sa.Integer(), nullable=False),
        sa.Column("failure_code", sa.String(length=80), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ingestion_jobs_user_status", "ingestion_jobs", ["user_id", "status"])
    op.create_index("ix_ingestion_jobs_document", "ingestion_jobs", ["document_id"])

    op.create_table(
        "embedding_cache",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("content_checksum", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("model", sa.String(length=180), nullable=False),
        sa.Column("dimension", sa.Integer(), nullable=False),
        sa.Column("vector", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_embedding_cache_key",
        "embedding_cache",
        ["content_checksum", "provider", "model", "dimension"],
        unique=True,
    )

    op.create_table(
        "memories",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("memory_type", sa.String(length=40), nullable=False),
        sa.Column("scope", sa.String(length=40), nullable=False),
        sa.Column("project_id", sa.String(length=120), nullable=True),
        sa.Column("conversation_id", sa.String(), nullable=True),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("source_message_id", sa.String(), nullable=True),
        sa.Column("importance", sa.Integer(), nullable=False),
        sa.Column("pinned", sa.Boolean(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("embedding_provider", sa.String(length=80), nullable=True),
        sa.Column("embedding_model", sa.String(length=180), nullable=True),
        sa.Column("embedding_dimension", sa.Integer(), nullable=True),
        sa.Column("relevance_hint", sa.Float(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.ForeignKeyConstraint(["source_message_id"], ["messages.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_memories_user_enabled_type_scope",
        "memories",
        ["user_id", "enabled", "memory_type", "scope"],
    )
    op.create_index(
        "ix_memories_user_pinned_updated", "memories", ["user_id", "pinned", "updated_at"]
    )
    op.create_index("ix_memories_project", "memories", ["project_id"])
    op.create_index("ix_memories_conversation", "memories", ["conversation_id"])
    op.create_index("ix_memories_source_message", "memories", ["source_message_id"])
    op.create_index("ix_memories_expires", "memories", ["expires_at"])
    op.create_index("ix_memories_checksum", "memories", ["checksum"])

    op.create_table(
        "memory_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("memory_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("actor", sa.String(length=40), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["memory_id"], ["memories.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_memory_events_memory", "memory_events", ["memory_id"])
    op.create_index("ix_memory_events_type", "memory_events", ["event_type"])

    op.create_table(
        "message_retrievals",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("message_id", sa.String(), nullable=False),
        sa.Column("chunk_id", sa.String(), nullable=True),
        sa.Column("memory_id", sa.String(), nullable=True),
        sa.Column("citation_id", sa.String(length=40), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["chunk_id"], ["document_chunks.id"]),
        sa.ForeignKeyConstraint(["memory_id"], ["memories.id"]),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_message_retrievals_message", "message_retrievals", ["message_id"])
    op.create_index("ix_message_retrievals_chunk", "message_retrievals", ["chunk_id"])


def downgrade() -> None:
    op.drop_index("ix_message_retrievals_chunk", table_name="message_retrievals")
    op.drop_index("ix_message_retrievals_message", table_name="message_retrievals")
    op.drop_table("message_retrievals")
    op.drop_index("ix_memory_events_type", table_name="memory_events")
    op.drop_index("ix_memory_events_memory", table_name="memory_events")
    op.drop_table("memory_events")
    op.drop_index("ix_memories_checksum", table_name="memories")
    op.drop_index("ix_memories_expires", table_name="memories")
    op.drop_index("ix_memories_source_message", table_name="memories")
    op.drop_index("ix_memories_conversation", table_name="memories")
    op.drop_index("ix_memories_project", table_name="memories")
    op.drop_index("ix_memories_user_pinned_updated", table_name="memories")
    op.drop_index("ix_memories_user_enabled_type_scope", table_name="memories")
    op.drop_table("memories")
    op.drop_index("uq_embedding_cache_key", table_name="embedding_cache")
    op.drop_table("embedding_cache")
    op.drop_index("ix_ingestion_jobs_document", table_name="ingestion_jobs")
    op.drop_index("ix_ingestion_jobs_user_status", table_name="ingestion_jobs")
    op.drop_table("ingestion_jobs")
    op.drop_index("ix_document_chunks_citation", table_name="document_chunks")
    op.drop_index("ix_document_chunks_checksum", table_name="document_chunks")
    op.drop_index("ix_document_chunks_user", table_name="document_chunks")
    op.drop_index("ix_document_chunks_document_index", table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_index("ix_documents_checksum", table_name="documents")
    op.drop_index("ix_documents_user_status_updated", table_name="documents")
    op.drop_table("documents")
