from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from access_control.models import AccessAudit, Document, KnowledgeHealthEvent, QueryLog, RoleEnum
from api.auth import CurrentUser
from database import get_db

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/overview")
async def overview(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    doc_count_result = await db.execute(select(func.count(Document.id)))
    doc_count = doc_count_result.scalar() or 0

    query_count_result = await db.execute(select(func.count(QueryLog.id)))
    query_count = query_count_result.scalar() or 0

    denial_count_result = await db.execute(
        select(func.count(AccessAudit.id)).where(AccessAudit.event_type == "denial")
    )
    denial_count = denial_count_result.scalar() or 0

    return {
        "document_count": doc_count,
        "total_queries": query_count,
        "access_denials": denial_count,
    }


@router.get("/query-history")
async def query_history(
    user: CurrentUser,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    result = await db.execute(
        select(QueryLog)
        .where(QueryLog.user_id == user.id)
        .order_by(QueryLog.timestamp.desc())
        .limit(limit)
    )
    rows = result.scalars().all()
    return [
        {
            "question": r.question,
            "retrieval_mode": r.retrieval_mode,
            "chunks_used": r.chunks_used,
            "mean_relevance_score": r.mean_relevance_score,
            "latency_ms": r.latency_ms,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
        }
        for r in rows
    ]


@router.get("/audit-log")
async def audit_log(
    user: CurrentUser,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    if user.role != RoleEnum.admin:
        # Non-admins only see their own audit entries
        result = await db.execute(
            select(AccessAudit)
            .where(AccessAudit.user_id == user.id)
            .order_by(AccessAudit.timestamp.desc())
            .limit(limit)
        )
    else:
        result = await db.execute(
            select(AccessAudit).order_by(AccessAudit.timestamp.desc()).limit(limit)
        )
    rows = result.scalars().all()
    return [
        {
            "event_type": r.event_type,
            "retrieval_mode": r.retrieval_mode,
            "caller_type": r.caller_type,
            "chunks_returned": len(r.returned_chunk_ids),
            "chunks_denied": len(r.denied_chunk_ids),
            "latency_ms": r.latency_ms,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
        }
        for r in rows
    ]


@router.get("/health-events")
async def health_events(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    if user.role != RoleEnum.admin:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Admin role required")
    result = await db.execute(
        select(KnowledgeHealthEvent)
        .where(KnowledgeHealthEvent.resolved == False)
        .order_by(KnowledgeHealthEvent.created_at.desc())
        .limit(50)
    )
    rows = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "event_type": r.event_type,
            "severity": r.severity,
            "title": r.title,
            "description": r.description,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
