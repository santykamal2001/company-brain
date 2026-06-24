"""Initial schema with AGE extension

Revision ID: 0001
Revises:
Create Date: 2026-06-16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable Apache AGE extension. Deliberately do NOT set search_path to
    # include ag_catalog here — doing so would make the unqualified
    # CREATE TABLE statements below land in ag_catalog instead of public.
    # AGE's own runtime search_path setup happens separately in
    # database.py::init_db() on a different connection.
    op.execute("CREATE EXTENSION IF NOT EXISTS age;")

    op.create_table(
        "departments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("username", sa.String(100), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=True),
        sa.Column("role", sa.Enum("admin", "manager", "employee", "guest", name="roleenum"), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id"), nullable=True),
        sa.Column("project_ids", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("idp_sub", sa.String(255), nullable=True),
        sa.Column("sso_provider", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_idp_sub", "users", ["idp_sub"])

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("source_path", sa.Text, nullable=True),
        sa.Column("source_url", sa.Text, nullable=True),
        sa.Column("file_hash", sa.String(64), nullable=True),
        sa.Column("file_size_bytes", sa.Integer, nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("chunk_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("classification", sa.Enum("public", "internal", "confidential", "restricted", name="classificationenum"), nullable=False, server_default="internal"),
        sa.Column("allowed_roles", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("allowed_departments", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("allowed_users", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("acl_version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_documents_file_hash", "documents", ["file_hash"])

    op.create_table(
        "chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_chunk_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chunks.id"), nullable=True),
        sa.Column("original_text", sa.Text, nullable=False),
        sa.Column("contextualized_text", sa.Text, nullable=True),
        sa.Column("embedding_model", sa.String(100), nullable=True),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("char_start", sa.Integer, nullable=False, server_default="0"),
        sa.Column("char_end", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_parent", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("acl_version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("entity_ids", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_chunks_document_id", "chunks", ["document_id"])

    op.create_table(
        "document_acl",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("classification", sa.Enum("public", "internal", "confidential", "restricted", name="classificationenum"), nullable=False),
        sa.Column("allowed_roles", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("allowed_departments", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("allowed_users", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("acl_version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "access_audit",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("event_type", sa.String(30), nullable=False, server_default="retrieval"),
        sa.Column("query_hash", sa.String(64), nullable=True),
        sa.Column("returned_chunk_ids", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("denied_chunk_ids", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("acl_version", sa.Integer, nullable=True),
        sa.Column("retrieval_mode", sa.String(20), nullable=True),
        sa.Column("caller_type", sa.String(20), nullable=False, server_default="human"),
        sa.Column("caller_agent_id", sa.String(255), nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_access_audit_timestamp", "access_audit", ["timestamp"])

    op.create_table(
        "query_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("retrieval_mode", sa.String(20), nullable=True),
        sa.Column("chunks_used", sa.Integer, nullable=False, server_default="0"),
        sa.Column("mean_relevance_score", sa.Float, nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_query_log_timestamp", "query_log", ["timestamp"])

    op.create_table(
        "knowledge_health_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("severity", sa.String(10), nullable=False, server_default="medium"),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("affected_document_ids", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("resolved", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("knowledge_health_events")
    op.drop_table("query_log")
    op.drop_table("access_audit")
    op.drop_table("document_acl")
    op.drop_table("chunks")
    op.drop_table("documents")
    op.drop_table("users")
    op.drop_table("departments")
    op.execute("DROP TYPE IF EXISTS roleenum;")
    op.execute("DROP TYPE IF EXISTS classificationenum;")
