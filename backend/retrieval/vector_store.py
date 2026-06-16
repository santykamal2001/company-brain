"""
Qdrant vector store: upsert and ACL-filtered hybrid (dense + sparse BM25) search.
Local BGE-large-en-v1.5 embeddings — no API calls, data stays on-premise.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from qdrant_client import AsyncQdrantClient, models
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)

from config import get_settings
from ingestion.chunker import ChunkResult

settings = get_settings()
log = logging.getLogger(__name__)

DENSE_VECTOR_NAME = "dense"
SPARSE_VECTOR_NAME = "sparse"


@lru_cache(maxsize=1)
def _get_embedding_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(settings.embedding_model)


@lru_cache(maxsize=1)
def _get_bm25_encoder():
    from qdrant_client.qdrant_fastembed import SparseTextEmbedding
    return SparseTextEmbedding(model_name="Qdrant/bm25")


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = _get_embedding_model()
    return model.encode(texts, normalize_embeddings=True, batch_size=32).tolist()


def bm25_encode(texts: list[str]) -> list[SparseVector]:
    encoder = _get_bm25_encoder()
    results = []
    for embedding in encoder.embed(texts):
        results.append(SparseVector(
            indices=embedding.indices.tolist(),
            values=embedding.values.tolist(),
        ))
    return results


def _qdrant_client() -> AsyncQdrantClient:
    return AsyncQdrantClient(url=settings.qdrant_url)


async def ensure_collection() -> None:
    client = _qdrant_client()
    existing = {c.name for c in (await client.get_collections()).collections}
    if settings.qdrant_collection not in existing:
        await client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config={
                DENSE_VECTOR_NAME: VectorParams(
                    size=settings.embedding_dim,
                    distance=Distance.COSINE,
                )
            },
            sparse_vectors_config={
                SPARSE_VECTOR_NAME: SparseVectorParams()
            },
        )
        # Create payload indexes for ACL filtering
        for role in ("admin", "manager", "employee", "guest"):
            await client.create_payload_index(
                collection_name=settings.qdrant_collection,
                field_name=f"allowed_role_{role}",
                field_schema="bool",
            )
        await client.create_payload_index(
            collection_name=settings.qdrant_collection,
            field_name="no_dept_restriction",
            field_schema="bool",
        )
        await client.create_payload_index(
            collection_name=settings.qdrant_collection,
            field_name="document_id",
            field_schema="keyword",
        )
    await client.close()


async def upsert_chunks(
    document_id: str,
    document_title: str,
    chunks: list[ChunkResult],
    base_payload: dict[str, Any],
) -> None:
    if not chunks:
        return

    texts_to_embed = [c.contextualized_text or c.original_text for c in chunks]
    dense_vectors = embed_texts(texts_to_embed)

    try:
        sparse_vectors = bm25_encode(texts_to_embed)
        has_sparse = True
    except Exception:
        has_sparse = False
        sparse_vectors = []

    client = _qdrant_client()
    points = []
    for i, chunk in enumerate(chunks):
        payload = {
            **base_payload,
            "document_id": document_id,
            "chunk_id": str(chunk.id),
            "chunk_index": chunk.chunk_index,
            "original_text": chunk.original_text,
            "char_start": chunk.char_start,
            "char_end": chunk.char_end,
        }
        vector: dict[str, Any] = {DENSE_VECTOR_NAME: dense_vectors[i]}
        if has_sparse and i < len(sparse_vectors):
            vector[SPARSE_VECTOR_NAME] = sparse_vectors[i]

        points.append(PointStruct(
            id=str(chunk.id),
            vector=vector,
            payload=payload,
        ))

    await client.upsert(collection_name=settings.qdrant_collection, points=points)
    await client.close()


async def search(
    query: str,
    acl_filter: dict,
    n: int = 32,
) -> list[dict[str, Any]]:
    """
    Hybrid search: dense cosine + sparse BM25, fused with RRF.
    acl_filter is the Qdrant filter dict from rbac.ACLContext.qdrant_filter().
    Returns list of payload dicts + score + id.
    """
    dense_vec = embed_texts([query])[0]

    client = _qdrant_client()
    qdrant_filter = Filter(**acl_filter) if acl_filter else None

    dense_results = await client.search(
        collection_name=settings.qdrant_collection,
        query_vector=(DENSE_VECTOR_NAME, dense_vec),
        query_filter=qdrant_filter,
        limit=n,
        with_payload=True,
    )

    sparse_results = []
    try:
        sparse_vec = bm25_encode([query])[0]
        sparse_results = await client.search(
            collection_name=settings.qdrant_collection,
            query_vector=models.NamedSparseVector(name=SPARSE_VECTOR_NAME, vector=sparse_vec),
            query_filter=qdrant_filter,
            limit=n,
            with_payload=True,
        )
    except Exception:
        pass

    await client.close()
    return _rrf_fuse(dense_results, sparse_results, k=60, top_n=n)


def _rrf_fuse(dense, sparse, k: int = 60, top_n: int = 32) -> list[dict]:
    scores: dict[str, float] = {}
    payloads: dict[str, dict] = {}

    for rank, hit in enumerate(dense):
        pid = str(hit.id)
        scores[pid] = scores.get(pid, 0) + 1 / (k + rank + 1)
        payloads[pid] = hit.payload or {}

    for rank, hit in enumerate(sparse):
        pid = str(hit.id)
        scores[pid] = scores.get(pid, 0) + 1 / (k + rank + 1)
        if pid not in payloads:
            payloads[pid] = hit.payload or {}

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
    return [
        {
            "id": pid,
            "score": score,
            **payloads[pid],
        }
        for pid, score in ranked
    ]


async def update_acl_payload(chunk_ids: list[str], acl_payload: dict) -> None:
    """Called when document permissions change. Metadata-only, no re-embedding."""
    client = _qdrant_client()
    from qdrant_client.models import SetPayload
    await client.set_payload(
        collection_name=settings.qdrant_collection,
        payload=acl_payload,
        points=chunk_ids,
    )
    await client.close()


async def delete_document_chunks(document_id: str) -> None:
    client = _qdrant_client()
    await client.delete(
        collection_name=settings.qdrant_collection,
        points_selector=Filter(
            must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
        ),
    )
    await client.close()
