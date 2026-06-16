import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database import Base


class RoleEnum(str, enum.Enum):
    admin = "admin"
    manager = "manager"
    employee = "employee"
    guest = "guest"


class ClassificationEnum(str, enum.Enum):
    public = "public"
    internal = "internal"
    confidential = "confidential"
    restricted = "restricted"


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    users: Mapped[list["User"]] = relationship("User", back_populates="department")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[RoleEnum] = mapped_column(Enum(RoleEnum), nullable=False, default=RoleEnum.employee)
    department_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True)
    project_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    idp_sub: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    sso_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    department: Mapped[Department | None] = relationship("Department", back_populates="users")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # filesystem|confluence|notion|slack|email
    source_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")  # pending|indexing|done|error
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    classification: Mapped[ClassificationEnum] = mapped_column(Enum(ClassificationEnum), nullable=False, default=ClassificationEnum.internal)
    allowed_roles: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    allowed_departments: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    allowed_users: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    acl_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    chunks: Mapped[list["Chunk"]] = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")
    acl: Mapped["DocumentACL | None"] = relationship("DocumentACL", back_populates="document", uselist=False, cascade="all, delete-orphan")


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_chunk_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("chunks.id"), nullable=True)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    contextualized_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    char_start: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    char_end: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_parent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    acl_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    entity_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document: Mapped[Document] = relationship("Document", back_populates="chunks")


class DocumentACL(Base):
    __tablename__ = "document_acl"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True)
    classification: Mapped[ClassificationEnum] = mapped_column(Enum(ClassificationEnum), nullable=False)
    allowed_roles: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    allowed_departments: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    allowed_users: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    acl_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    document: Mapped[Document] = relationship("Document", back_populates="acl")


class AccessAudit(Base):
    __tablename__ = "access_audit"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False, default="retrieval")  # retrieval|action|mcp_query|denial
    query_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    returned_chunk_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    denied_chunk_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    acl_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retrieval_mode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    caller_type: Mapped[str] = mapped_column(String(20), nullable=False, default="human")  # human|mcp_agent
    caller_agent_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class QueryLog(Base):
    __tablename__ = "query_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    retrieval_mode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    chunks_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mean_relevance_score: Mapped[float | None] = mapped_column(nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class KnowledgeHealthEvent(Base):
    __tablename__ = "knowledge_health_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)  # stale_alert|conflict_alert|gap_report|acl_drift_alert|orphaned_decision_alert
    severity: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")  # low|medium|high
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    affected_document_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
