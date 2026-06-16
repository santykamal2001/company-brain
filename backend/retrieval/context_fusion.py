"""
Merges vector chunks + graph triples + decision trail into a single LLM context string.
"""
from __future__ import annotations

from llm.prompts import (
    DECISION_CONTEXT_HEADER,
    DOCUMENT_CONTEXT_HEADER,
    GRAPH_CONTEXT_HEADER,
)


def build_context(
    chunks: list[dict],
    graph_triples: list[str],
    decision_context: list[dict],
    mode: str,
) -> str:
    parts: list[str] = []

    if mode in ("graph", "hybrid", "decision") and graph_triples:
        parts.append(GRAPH_CONTEXT_HEADER)
        parts.extend(graph_triples)

    if decision_context:
        parts.append(DECISION_CONTEXT_HEADER)
        for d in decision_context:
            raw = d.get("raw", "")
            parts.append(f"• {raw}")

    if chunks:
        parts.append(DOCUMENT_CONTEXT_HEADER)
        for chunk in chunks:
            doc_title = chunk.get("document_title", "Unknown Document")
            score = chunk.get("rerank_score") or chunk.get("score") or 0
            text = chunk.get("original_text") or chunk.get("text") or ""
            parts.append(
                f"[Source: {doc_title} | relevance: {score:.3f}]\n{text}"
            )

    return "\n\n".join(parts)


def build_user_message(question: str, context: str) -> str:
    return (
        f"Based on the following company knowledge, answer this question:\n\n"
        f"QUESTION: {question}\n\n"
        f"{context}\n\n"
        f"Provide a clear, specific answer citing source documents."
    )
