"""
Cross-encoder reranker. Loaded lazily on first call; singleton thereafter.
Falls back to score-order if the reranker fails to load.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

log = logging.getLogger(__name__)

RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


@lru_cache(maxsize=1)
def _load_reranker():
    try:
        from sentence_transformers import CrossEncoder
        model = CrossEncoder(RERANKER_MODEL)
        log.info(f"Reranker loaded: {RERANKER_MODEL}")
        return model
    except Exception as exc:
        log.warning(f"Reranker unavailable: {exc}")
        return None


def rerank(
    question: str,
    chunks: list[dict[str, Any]],
    top_k: int = 8,
) -> list[dict[str, Any]]:
    """Re-score chunks with cross-encoder and return top_k."""
    if not chunks:
        return []

    model = _load_reranker()
    if model is None:
        return chunks[:top_k]

    try:
        texts = [c.get("original_text") or c.get("text") or "" for c in chunks]
        pairs = [(question, t) for t in texts]
        scores = model.predict(pairs)
        for i, chunk in enumerate(chunks):
            chunk["rerank_score"] = float(scores[i])
        ranked = sorted(chunks, key=lambda x: x.get("rerank_score", 0), reverse=True)
        return ranked[:top_k]
    except Exception as exc:
        log.warning(f"Reranking failed: {exc}")
        return chunks[:top_k]
