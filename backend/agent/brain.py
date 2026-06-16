"""
Main ask() orchestrator: routes → retrieves → filters → generates → audits.

Pipeline:
  1. classify query mode (vector | graph | hybrid | decision)
  2. vector search with ACL pre-filter
  3. cross-encoder rerank
  4. graph traversal (if mode != vector)
  5. decision context (if mode == decision)
  6. RBAC post-filter (Postgres source-of-truth)
  7. context fusion
  8. LLM generation
  9. audit log
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from access_control.audit import log_retrieval
from access_control.rbac import ACLContext, post_filter_chunks
from config import get_settings
from llm.adapter import get_llm
from llm.prompts import COMPANY_BRAIN_SYSTEM
from retrieval.context_fusion import build_context, build_user_message
from retrieval.graph_retrieval import format_decisions, format_graph_triples, get_decision_context, get_graph_context
from retrieval.query_router import classify
from retrieval.reranker import rerank
from retrieval.vector_store import search

settings = get_settings()


@dataclass
class AskResponse:
    answer: str
    sources: list[dict] = field(default_factory=list)
    chunks_used: int = 0
    latency_ms: int = 0
    retrieval_mode: str = "vector"
    graph_entities_used: list[str] = field(default_factory=list)
    decision_trail_used: bool = False
    denied_chunk_count: int = 0


async def ask(
    question: str,
    acl: ACLContext,
    db: AsyncSession,
    n_results: int = 8,
) -> AskResponse:
    t_start = time.perf_counter()

    # 1. Route
    route = await classify(question)

    # 2. Vector search with Qdrant ACL pre-filter
    candidates = await search(
        query=question,
        acl_filter=acl.qdrant_filter(),
        n=max(n_results * 4, 32),
    )

    # 3. Rerank
    reranked = rerank(question, candidates, top_k=n_results * 2)

    # 4. Graph context
    graph_triples: list[str] = []
    if settings.graph_enabled and route.mode in ("graph", "hybrid", "decision"):
        graph_triples = await get_graph_context(
            entity_names=route.entities_mentioned,
            acl_roles=[acl.role.value],
            mode=route.mode,
        )

    # 5. Decision context
    decision_context: list[dict] = []
    if route.mode == "decision":
        decision_context = await get_decision_context(limit=10)

    # 6. RBAC post-filter (Postgres source-of-truth — catches stale Qdrant payloads)
    chunk_ids = [str(c.get("chunk_id") or c.get("id")) for c in reranked if c.get("chunk_id") or c.get("id")]
    allowed_ids, denied_ids = await post_filter_chunks(chunk_ids, acl, db)
    allowed_set = set(allowed_ids)
    final_chunks = [
        c for c in reranked
        if str(c.get("chunk_id") or c.get("id")) in allowed_set
    ][:n_results]

    # 7. Context fusion
    context = build_context(
        chunks=final_chunks,
        graph_triples=graph_triples,
        decision_context=decision_context,
        mode=route.mode,
    )

    # 8. LLM generation
    llm = get_llm()
    user_message = build_user_message(question, context)
    llm_resp = await llm.complete(
        system=COMPANY_BRAIN_SYSTEM,
        user=user_message,
        max_tokens=2048,
    )

    latency_ms = int((time.perf_counter() - t_start) * 1000)

    # 9. Audit log (fire-and-forget; don't block response)
    try:
        await log_retrieval(
            db=db,
            acl=acl,
            question=question,
            returned_chunk_ids=allowed_ids,
            denied_chunk_ids=denied_ids,
            retrieval_mode=route.mode,
            acl_version=None,
            latency_ms=latency_ms,
        )
    except Exception:
        pass

    return AskResponse(
        answer=llm_resp.text,
        sources=[
            {
                "document_title": c.get("document_title", ""),
                "chunk_id": c.get("chunk_id") or c.get("id"),
                "score": round(c.get("rerank_score") or c.get("score") or 0, 4),
                "excerpt": (c.get("original_text") or "")[:300],
                "char_start": c.get("char_start"),
                "char_end": c.get("char_end"),
            }
            for c in final_chunks
        ],
        chunks_used=len(final_chunks),
        latency_ms=latency_ms,
        retrieval_mode=route.mode,
        graph_entities_used=route.entities_mentioned,
        decision_trail_used=bool(decision_context),
        denied_chunk_count=len(denied_ids),
    )
