"""
Main ask() orchestrator: routes → retrieves (parallel) → filters → generates → audits.

Pipeline:
  1. classify query mode (vector | graph | hybrid | decision)
  2. vector search with ACL pre-filter
  3. PARALLEL: rerank (thread pool) + graph traversal + decision context
  4. RBAC post-filter (Postgres source-of-truth)
  5. context fusion
  6. LLM generation (blocking) or streaming (ask_stream)
  7. audit log

Parallelism:
  Steps 3a/3b/3c are fully independent once vector results are available.
  Running them via asyncio.gather() hides the reranker's CPU time behind
  the concurrent graph/decision network I/O.
"""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from access_control.audit import log_retrieval
from access_control.rbac import ACLContext, post_filter_chunks
from config import get_settings
from llm.adapter import get_llm
from llm.prompts import COMPANY_BRAIN_SYSTEM
from retrieval.context_fusion import build_context, build_user_message
from retrieval.graph_retrieval import format_decisions, format_graph_triples, get_decision_context, get_graph_context
from retrieval.query_router import classify
from retrieval.reranker import rerank_async
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


def _build_sources(chunks: list[dict]) -> list[dict]:
    return [
        {
            "document_title": c.get("document_title", ""),
            "chunk_id": c.get("chunk_id") or c.get("id"),
            "score": round(c.get("rerank_score") or c.get("score") or 0, 4),
            "excerpt": (c.get("original_text") or "")[:300],
            "char_start": c.get("char_start"),
            "char_end": c.get("char_end"),
        }
        for c in chunks
    ]


async def _retrieve(
    question: str,
    acl: ACLContext,
    db: AsyncSession,
    n_results: int,
    route,
) -> tuple[list[dict], list[str], list[dict], list[str], list[str]]:
    """
    Run vector search, then in parallel: rerank + graph context + decision context.
    Returns (final_chunks, allowed_ids, denied_ids, graph_triples, decision_context).
    """
    # Vector search
    candidates = await search(
        query=question,
        acl_filter=acl.qdrant_filter(),
        n=max(n_results * 4, 32),
    )

    needs_graph = settings.graph_enabled and route.mode in ("graph", "hybrid", "decision")
    needs_decision = route.mode == "decision"

    # Build parallel tasks — reranker is CPU-bound so it runs in a thread pool
    async def _no_graph() -> list[str]:
        return []

    async def _no_decision() -> list[dict]:
        return []

    results = await asyncio.gather(
        rerank_async(question, candidates, top_k=n_results * 2),
        get_graph_context(
            entity_names=route.entities_mentioned,
            acl_roles=[acl.role.value],
            mode=route.mode,
        ) if needs_graph else _no_graph(),
        get_decision_context(limit=10) if needs_decision else _no_decision(),
    )

    reranked: list[dict] = results[0]
    graph_triples: list[str] = results[1]
    decision_context: list[dict] = results[2]

    # RBAC post-filter
    chunk_ids = [str(c.get("chunk_id") or c.get("id")) for c in reranked if c.get("chunk_id") or c.get("id")]
    allowed_ids, denied_ids = await post_filter_chunks(chunk_ids, acl, db)
    allowed_set = set(allowed_ids)
    final_chunks = [
        c for c in reranked
        if str(c.get("chunk_id") or c.get("id")) in allowed_set
    ][:n_results]

    return final_chunks, allowed_ids, denied_ids, graph_triples, decision_context


async def ask(
    question: str,
    acl: ACLContext,
    db: AsyncSession,
    n_results: int = 8,
) -> AskResponse:
    t_start = time.perf_counter()

    route = await classify(question)

    final_chunks, allowed_ids, denied_ids, graph_triples, decision_context = await _retrieve(
        question, acl, db, n_results, route
    )

    context = build_context(
        chunks=final_chunks,
        graph_triples=graph_triples,
        decision_context=decision_context,
        mode=route.mode,
    )

    llm = get_llm()
    user_message = build_user_message(question, context)
    llm_resp = await llm.complete(
        system=COMPANY_BRAIN_SYSTEM,
        user=user_message,
        max_tokens=2048,
    )

    latency_ms = int((time.perf_counter() - t_start) * 1000)

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
        sources=_build_sources(final_chunks),
        chunks_used=len(final_chunks),
        latency_ms=latency_ms,
        retrieval_mode=route.mode,
        graph_entities_used=route.entities_mentioned,
        decision_trail_used=bool(decision_context),
        denied_chunk_count=len(denied_ids),
    )


async def ask_stream(
    question: str,
    acl: ACLContext,
    db: AsyncSession,
    n_results: int = 8,
) -> AsyncIterator[str]:
    """
    Streaming variant. Yields SSE-formatted strings:
      event: metadata\\ndata: <json>\\n\\n   — retrieval info, sources, timing
      event: token\\ndata: <json token>\\n\\n — one per LLM output token
      event: done\\ndata: <json>\\n\\n        — total latency_ms

    The frontend can start rendering tokens immediately while the metadata
    event arrives first with sources and retrieval mode.
    """
    t_start = time.perf_counter()

    route = await classify(question)

    final_chunks, allowed_ids, denied_ids, graph_triples, decision_context = await _retrieve(
        question, acl, db, n_results, route
    )

    context = build_context(
        chunks=final_chunks,
        graph_triples=graph_triples,
        decision_context=decision_context,
        mode=route.mode,
    )

    t_retrieval_ms = int((time.perf_counter() - t_start) * 1000)

    # Emit metadata so the frontend can render source cards before LLM starts
    metadata = {
        "retrieval_mode": route.mode,
        "graph_entities_used": route.entities_mentioned,
        "decision_trail_used": bool(decision_context),
        "chunks_used": len(final_chunks),
        "denied_chunk_count": len(denied_ids),
        "retrieval_ms": t_retrieval_ms,
        "sources": _build_sources(final_chunks),
    }
    yield f"event: metadata\ndata: {json.dumps(metadata)}\n\n"

    # Stream LLM tokens
    llm = get_llm()
    user_message = build_user_message(question, context)
    full_answer = ""

    async for token in llm.stream(
        system=COMPANY_BRAIN_SYSTEM,
        user=user_message,
        max_tokens=2048,
    ):
        full_answer += token
        yield f"event: token\ndata: {json.dumps(token)}\n\n"

    total_ms = int((time.perf_counter() - t_start) * 1000)
    yield f"event: done\ndata: {json.dumps({'latency_ms': total_ms})}\n\n"

    try:
        await log_retrieval(
            db=db,
            acl=acl,
            question=question,
            returned_chunk_ids=allowed_ids,
            denied_chunk_ids=denied_ids,
            retrieval_mode=route.mode,
            acl_version=None,
            latency_ms=total_ms,
        )
    except Exception:
        pass
