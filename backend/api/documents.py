from __future__ import annotations

import os
import uuid
from pathlib import Path
from uuid import UUID

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from access_control.models import ClassificationEnum, Document, RoleEnum
from api.auth import CurrentUser
from config import get_settings
from database import get_db

router = APIRouter(prefix="/api/documents", tags=["documents"])
settings = get_settings()

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt",
                      ".txt", ".md", ".csv", ".rtf", ".odt"}


class UpdateACLRequest(BaseModel):
    classification: ClassificationEnum | None = None
    allowed_roles: list[str] | None = None
    allowed_departments: list[str] | None = None


@router.post("/upload", status_code=202)
async def upload_document(
    file: UploadFile = File(...),
    classification: str = Form(default="internal"),
    allowed_departments: str = Form(default=""),
    user: CurrentUser = Depends(),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if user.role not in (RoleEnum.admin, RoleEnum.manager):
        raise HTTPException(status_code=403, detail="Manager or Admin role required to upload")

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail=f"Unsupported file type: {suffix}")

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    doc_id = uuid.uuid4()
    dest_path = upload_dir / f"{doc_id}{suffix}"

    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail="File too large")

    async with aiofiles.open(dest_path, "wb") as f:
        await f.write(content)

    dept_list = [d.strip() for d in allowed_departments.split(",") if d.strip()]
    try:
        cls = ClassificationEnum(classification)
    except ValueError:
        cls = ClassificationEnum.internal

    doc = Document(
        id=doc_id,
        title=file.filename or str(doc_id),
        source_type="filesystem",
        source_path=str(dest_path),
        file_size_bytes=len(content),
        mime_type=file.content_type,
        status="pending",
        classification=cls,
        allowed_roles=[],
        allowed_departments=dept_list,
        allowed_users=[],
        uploaded_by=user.id,
    )
    db.add(doc)
    await db.commit()

    # Queue background ingestion
    from ingestion.worker import process_document
    process_document.delay(str(doc_id), str(dest_path))

    return {"document_id": str(doc_id), "status": "queued", "title": doc.title}


@router.get("/")
async def list_documents(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    result = await db.execute(
        select(Document).order_by(Document.created_at.desc()).limit(200)
    )
    docs = result.scalars().all()
    return [_doc_dict(d) for d in docs]


@router.get("/{document_id}")
async def get_document(
    document_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    doc = await db.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return _doc_dict(doc)


@router.patch("/{document_id}/acl")
async def update_document_acl(
    document_id: UUID,
    body: UpdateACLRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    if user.role not in (RoleEnum.admin, RoleEnum.manager):
        raise HTTPException(status_code=403, detail="Manager or Admin required")

    doc = await db.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if body.classification:
        doc.classification = body.classification
    if body.allowed_roles is not None:
        doc.allowed_roles = body.allowed_roles
    if body.allowed_departments is not None:
        doc.allowed_departments = body.allowed_departments

    doc.acl_version += 1
    await db.commit()

    # Push ACL update to Qdrant (metadata only, no re-embedding)
    from access_control.rbac import acl_payload_for_chunk
    from retrieval.vector_store import update_acl_payload
    from access_control.models import Chunk
    chunk_result = await db.execute(select(Chunk.id).where(Chunk.document_id == document_id))
    chunk_ids = [str(r[0]) for r in chunk_result.fetchall()]
    if chunk_ids:
        acl_payload = acl_payload_for_chunk(
            classification=doc.classification,
            allowed_roles=doc.allowed_roles,
            allowed_departments=doc.allowed_departments,
            allowed_users=doc.allowed_users,
        )
        await update_acl_payload(chunk_ids, acl_payload)

    return _doc_dict(doc)


@router.post("/{document_id}/reindex", status_code=202)
async def reindex_document(
    document_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    if user.role not in (RoleEnum.admin, RoleEnum.manager):
        raise HTTPException(status_code=403, detail="Manager or Admin required")

    doc = await db.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not doc.source_path:
        raise HTTPException(status_code=400, detail="No source file path on record")

    doc.file_hash = None  # Force re-index
    doc.status = "pending"
    await db.commit()

    from ingestion.worker import process_document
    process_document.delay(str(document_id), doc.source_path)

    return {"document_id": str(document_id), "status": "queued"}


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    if user.role != RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Admin role required")

    doc = await db.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    from retrieval.vector_store import delete_document_chunks
    await delete_document_chunks(str(document_id))

    await db.delete(doc)
    await db.commit()


def _doc_dict(doc: Document) -> dict:
    return {
        "id": str(doc.id),
        "title": doc.title,
        "source_type": doc.source_type,
        "status": doc.status,
        "chunk_count": doc.chunk_count,
        "classification": doc.classification.value if doc.classification else None,
        "allowed_departments": doc.allowed_departments,
        "file_size_bytes": doc.file_size_bytes,
        "error_message": doc.error_message,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
    }
