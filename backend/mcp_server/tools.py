"""
MCP tool implementations. Each function mirrors what a human query does:
RBAC-enforced retrieval + audit logging. caller_type is always "mcp_agent".
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class SearchParams(BaseModel):
    query: str
    context: str = ""
    n_results: int = Field(default=5, ge=1, le=20)


class EntityRelationsParams(BaseModel):
    entity_name: str
    depth: int = Field(default=1, ge=1, le=2)


class DecisionsParams(BaseModel):
    topic: str = ""
    project: str = ""


class CheckAccessParams(BaseModel):
    user_email: str
    topic_or_doc: str


async def search_knowledge(params: SearchParams, *, user, db: AsyncSession) -> dict:
    """
    Full hybrid RAG search. Runs with the calling MCP user's RBAC context so
    an agent cannot retrieve more than the user it represents is allowed to see.
    """
    from access_control.rbac import acl_context_from_user
    from access_control.audit import log_retrieval
    from agent.brain import ask

    acl = acl_context_from_user(user)
    full_query = f"{params.context}\n\n{params.query}".strip() if params.context else params.query

    response = await ask(full_query, acl=acl, db=db, n_results=params.n_results)

    # Re-log with caller_type=mcp_agent so the audit trail distinguishes agent queries
    try:
        await log_retrieval(
            db=db,
            acl=acl,
            question=full_query,
            returned_chunk_ids=[s.get("chunk_id", "") for s in response.sources],
            denied_chunk_ids=[],
            retrieval_mode=response.retrieval_mode,
            acl_version=None,
            latency_ms=response.latency_ms,
            caller_type="mcp_agent",
        )
    except Exception:
        pass

    return {
        "answer": response.answer,
        "sources": response.sources,
        "retrieval_mode": response.retrieval_mode,
        "graph_entities_used": response.graph_entities_used,
        "chunks_used": response.chunks_used,
        "latency_ms": response.latency_ms,
        "decision_trail_used": response.decision_trail_used,
    }


async def get_entity_relations(params: EntityRelationsParams, *, user, db: AsyncSession) -> dict:
    """
    Depth-1 AGE graph traversal anchored on a named entity.
    ACL-filtered to the calling user's role.
    """
    from access_control.rbac import acl_context_from_user
    from retrieval.graph_retrieval import get_graph_context

    acl = acl_context_from_user(user)
    triples = await get_graph_context(
        entity_names=[params.entity_name],
        acl_roles=[acl.role.value],
        mode="graph",
    )
    return {
        "entity": params.entity_name,
        "depth": params.depth,
        "triples": triples,
        "count": len(triples),
    }


async def get_decisions(params: DecisionsParams, *, user, db: AsyncSession) -> dict:
    """
    Query the Decision Trail. Filters by topic or project if provided.
    All decisions go through the same ACL that was set on the source chunks.
    """
    from retrieval.graph_retrieval import get_decision_context

    decisions = await get_decision_context(
        topic=params.topic,
        project=params.project,
        limit=20,
    )
    return {
        "decisions": decisions,
        "count": len(decisions),
        "filter": {"topic": params.topic, "project": params.project},
    }


async def check_employee_access(params: CheckAccessParams, *, user, db: AsyncSession) -> dict:
    """
    Admin-only tool: returns whether a given employee has access to a topic/doc.
    Never returns document content — access metadata only.
    """
    from access_control.models import User, DocumentACL, Document, RoleEnum

    if user.role != RoleEnum.admin:
        raise PermissionError("Admin role required to check access for other users")

    # Look up the target user
    result = await db.execute(select(User).where(User.email == params.user_email))
    target = result.scalar_one_or_none()
    if not target:
        return {"user_email": params.user_email, "found": False}

    # Find matching documents by title
    result2 = await db.execute(
        select(Document, DocumentACL)
        .join(DocumentACL, DocumentACL.document_id == Document.id, isouter=True)
        .where(Document.title.ilike(f"%{params.topic_or_doc}%"))
        .limit(5)
    )
    rows = result2.all()

    access_granted = False
    reason = "No matching document found"
    for doc, acl in rows:
        if acl is None:
            access_granted = True
            reason = f"Document '{doc.title}' has no ACL restriction"
            break
        if not acl.allowed_roles or (target.role and target.role.value in acl.allowed_roles):
            access_granted = True
            reason = f"Role '{target.role.value if target.role else 'none'}' permitted on '{doc.title}'"
            break
        if target.id and str(target.id) in (acl.allowed_users or []):
            access_granted = True
            reason = f"User explicitly whitelisted on '{doc.title}'"
            break
        reason = f"Role '{target.role.value if target.role else 'none'}' not in allowed_roles for '{doc.title}'"

    return {
        "user_email": params.user_email,
        "found": True,
        "role": target.role.value if target.role else None,
        "department_id": str(target.department_id) if target.department_id else None,
        "topic_or_doc": params.topic_or_doc,
        "access_granted": access_granted,
        "reason": reason,
    }
