"""
Knowledge Health Monitor — Celery beat task (default: daily).
Writes KnowledgeHealthEvent rows for stale content, coverage gaps,
permission drift, and orphaned decisions.

Celery beat config is in worker.py. Add to your Celery beat schedule:
    "run-health-check": {
        "task": "quality_monitor.run_health_check",
        "schedule": crontab(hour=3, minute=0),  # 3 AM daily
    }
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

from celery import shared_task
from sqlalchemy import func, select, text

log = logging.getLogger(__name__)

_STALE_DAYS = 180           # Docs not updated for this many days…
_STALE_MIN_QUERIES = 3      # …but retrieved at least this many times recently
_GAP_SCORE_THRESHOLD = 0.4  # Queries below this relevance score → coverage gap
_RECENT_DAYS = 30           # "Recent" window for stale + gap checks
_ACL_DRIFT_VERSIONS = 2     # Chunk vs doc ACL version drift threshold


@shared_task(name="quality_monitor.run_health_check")
def run_health_check() -> str:
    """Celery task entry point — wraps the async check."""
    count = asyncio.run(_async_run())
    return f"Health check complete: {count} events written"


async def _async_run() -> int:
    from database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        events: list[dict] = []
        events += await _stale_content(db)
        events += await _coverage_gaps(db)
        events += await _permission_drift(db)
        events += await _orphaned_decisions(db)

        if events:
            from access_control.models import KnowledgeHealthEvent
            for ev in events:
                db.add(KnowledgeHealthEvent(**ev))
            await db.commit()
            log.info("Health check: %d new events", len(events))
        else:
            log.info("Health check: no issues found")

    return len(events)


async def _stale_content(db) -> list[dict]:
    """Docs last updated > 180 days ago that are still being queried."""
    from access_control.models import Document, QueryLog

    cutoff_stale = datetime.now(timezone.utc) - timedelta(days=_STALE_DAYS)
    cutoff_recent = datetime.now(timezone.utc) - timedelta(days=_RECENT_DAYS)

    result = await db.execute(
        select(Document.id, Document.title, Document.updated_at)
        .where(Document.updated_at < cutoff_stale)
        .where(Document.status == "done")
    )
    stale_docs = result.all()

    # Count recent query activity
    q_result = await db.execute(
        select(func.count(QueryLog.id)).where(QueryLog.timestamp > cutoff_recent)
    )
    recent_query_count = q_result.scalar() or 0

    events = []
    if recent_query_count >= _STALE_MIN_QUERIES:
        for doc_id, title, updated_at in stale_docs:
            days_old = (datetime.now(timezone.utc) - updated_at.replace(tzinfo=timezone.utc)).days
            events.append({
                "id": uuid.uuid4(),
                "event_type": "stale_content",
                "severity": "medium",
                "title": f"Stale document: {title}",
                "description": (
                    f"'{title}' was last updated {days_old} days ago but is still being queried. "
                    f"Consider updating or archiving it."
                ),
                "affected_document_ids": [str(doc_id)],
                "resolved": False,
            })
    return events


async def _coverage_gaps(db) -> list[dict]:
    """Queries in the last 30 days with very low relevance — knowledge gaps."""
    from access_control.models import QueryLog

    cutoff = datetime.now(timezone.utc) - timedelta(days=_RECENT_DAYS)
    result = await db.execute(
        select(QueryLog.question, QueryLog.mean_relevance_score)
        .where(QueryLog.timestamp > cutoff)
        .where(QueryLog.mean_relevance_score != None)
        .where(QueryLog.mean_relevance_score < _GAP_SCORE_THRESHOLD)
        .order_by(QueryLog.timestamp.desc())
        .limit(25)
    )
    gap_queries = result.all()

    if not gap_queries:
        return []

    samples = "; ".join(q.question[:80] for q in gap_queries[:5])
    return [{
        "id": uuid.uuid4(),
        "event_type": "coverage_gap",
        "severity": "high",
        "title": f"Knowledge gap: {len(gap_queries)} low-relevance queries in last {_RECENT_DAYS} days",
        "description": (
            f"{len(gap_queries)} queries returned results with mean relevance < {_GAP_SCORE_THRESHOLD}. "
            f"These topics may not be well covered in the knowledge base. "
            f"Sample questions: {samples}"
        ),
        "affected_document_ids": [],
        "resolved": False,
    }]


async def _permission_drift(db) -> list[dict]:
    """Chunks whose ACL version drifted > 2 from their parent document."""
    try:
        result = await db.execute(text("""
            SELECT d.id::text, d.title, d.acl_version, COUNT(c.id) AS drift_count
            FROM documents d
            JOIN chunks c ON c.document_id = d.id
            WHERE ABS(COALESCE(c.acl_version, 0) - COALESCE(d.acl_version, 0)) > :drift
            GROUP BY d.id, d.title, d.acl_version
            HAVING COUNT(c.id) > 0
        """), {"drift": _ACL_DRIFT_VERSIONS})
        drifted = result.all()
    except Exception as exc:
        log.warning("permission_drift check failed: %s", exc)
        return []

    return [
        {
            "id": uuid.uuid4(),
            "event_type": "permission_drift",
            "severity": "high",
            "title": f"Permission drift: {title}",
            "description": (
                f"Document '{title}' has {drift_count} chunks with ACL version "
                f"mismatched by >{_ACL_DRIFT_VERSIONS} from the document "
                f"(doc_acl_version={doc_version}). Run a re-index or trigger "
                f"update_acl_payload() to sync Qdrant payloads."
            ),
            "affected_document_ids": [doc_id],
            "resolved": False,
        }
        for doc_id, title, doc_version, drift_count in drifted
    ]


async def _orphaned_decisions(db) -> list[dict]:
    """Decision graph nodes whose evidence chunks no longer exist in Postgres."""
    try:
        from retrieval.graph_store import query_decisions
        decisions = await query_decisions(limit=100)
    except Exception:
        return []

    if not decisions:
        return []

    from access_control.models import Chunk

    events = []
    for d in decisions:
        evidence_ids = d.get("evidence_chunk_ids") or []
        if not evidence_ids:
            continue
        # Check if any evidence chunk still exists
        result = await db.execute(
            select(func.count(Chunk.id)).where(
                Chunk.id.in_([uuid.UUID(eid) for eid in evidence_ids if _is_valid_uuid(eid)])
            )
        )
        found = result.scalar() or 0
        if found == 0:
            events.append({
                "id": uuid.uuid4(),
                "event_type": "orphaned_decision",
                "severity": "medium",
                "title": f"Orphaned decision: {d.get('title', 'unknown')}",
                "description": (
                    f"Decision '{d.get('title', '')}' references {len(evidence_ids)} "
                    f"evidence chunks that no longer exist. The decision record may be stale."
                ),
                "affected_document_ids": [],
                "resolved": False,
            })
    return events


def _is_valid_uuid(val: str) -> bool:
    try:
        uuid.UUID(val)
        return True
    except Exception:
        return False
