from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from access_control.models import AccessAudit
from access_control.rbac import ACLContext, query_hash


async def log_retrieval(
    db: AsyncSession,
    acl: ACLContext,
    question: str,
    returned_chunk_ids: list[str],
    denied_chunk_ids: list[str],
    retrieval_mode: str,
    acl_version: int | None,
    latency_ms: int | None = None,
    caller_type: str = "human",
    caller_agent_id: str | None = None,
) -> None:
    event = AccessAudit(
        user_id=UUID(acl.user_id) if acl.user_id else None,
        event_type="retrieval" if returned_chunk_ids else "denial",
        query_hash=query_hash(question),
        returned_chunk_ids=returned_chunk_ids,
        denied_chunk_ids=denied_chunk_ids,
        acl_version=acl_version,
        retrieval_mode=retrieval_mode,
        caller_type=caller_type,
        caller_agent_id=caller_agent_id,
        latency_ms=latency_ms,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(event)
    await db.commit()


async def log_action(
    db: AsyncSession,
    acl: ACLContext,
    action_type: str,
    latency_ms: int | None = None,
) -> None:
    event = AccessAudit(
        user_id=UUID(acl.user_id) if acl.user_id else None,
        event_type="action",
        query_hash=None,
        returned_chunk_ids=[],
        denied_chunk_ids=[],
        retrieval_mode=action_type,
        caller_type="human",
        latency_ms=latency_ms,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(event)
    await db.commit()
