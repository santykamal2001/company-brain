from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from access_control.rbac import acl_context_from_user
from agent.brain import ask, ask_stream
from api.auth import CurrentUser
from database import get_db

router = APIRouter(prefix="/api/query", tags=["query"])


class QueryRequest(BaseModel):
    question: str
    n_results: int = 8


class QueryResponse(BaseModel):
    answer: str
    sources: list[dict]
    chunks_used: int
    latency_ms: int
    retrieval_mode: str
    graph_entities_used: list[str]
    decision_trail_used: bool
    denied_chunk_count: int


@router.post("/", response_model=QueryResponse)
async def query(
    body: QueryRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> QueryResponse:
    acl = acl_context_from_user(user)
    response = await ask(
        question=body.question,
        acl=acl,
        db=db,
        n_results=min(body.n_results, 20),
    )
    return QueryResponse(
        answer=response.answer,
        sources=response.sources,
        chunks_used=response.chunks_used,
        latency_ms=response.latency_ms,
        retrieval_mode=response.retrieval_mode,
        graph_entities_used=response.graph_entities_used,
        decision_trail_used=response.decision_trail_used,
        denied_chunk_count=response.denied_chunk_count,
    )


@router.post("/stream")
async def query_stream(
    body: QueryRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    SSE streaming endpoint. Returns text/event-stream with three event types:
      metadata — retrieval info + sources (arrives before first token)
      token    — one LLM output token (arrives as generated)
      done     — total latency_ms

    Clients should use EventSource or fetch+ReadableStream to consume.
    """
    acl = acl_context_from_user(user)

    async def generate():
        async for chunk in ask_stream(
            question=body.question,
            acl=acl,
            db=db,
            n_results=min(body.n_results, 20),
        ):
            yield chunk

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering
        },
    )
