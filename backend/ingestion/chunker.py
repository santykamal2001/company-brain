"""
Hierarchical chunking with optional Contextual Retrieval.

Produces:
  - parent chunks (~3000-4000 chars, section-level)
  - child chunks (512 chars / 50 overlap) — each records parent_chunk_id

For contextual retrieval, calls the context LLM with the full document as a
cached prefix and prepends a 50-100 word situating context to each child chunk.
The result is stored as `contextualized_text`; `original_text` is always preserved
for citation display and must never be replaced.
"""
from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from config import get_settings
from llm.adapter import ClaudeClient, get_context_llm
from llm.prompts import CONTEXTUAL_RETRIEVAL_SYSTEM

settings = get_settings()

CONTEXT_PROMPT_TEMPLATE = (
    "<document>{document_text}</document>\n"
    "<chunk>{chunk_text}</chunk>\n"
    "Give a short succinct context (50-100 words) situating this chunk within "
    "the overall document for retrieval purposes. Answer only with the context, no preamble."
)


@dataclass
class ChunkResult:
    id: UUID = field(default_factory=uuid4)
    parent_id: UUID | None = None
    original_text: str = ""
    contextualized_text: str | None = None
    chunk_index: int = 0
    char_start: int = 0
    char_end: int = 0
    is_parent: bool = False


def chunk_document(
    text: str,
    parent_size: int | None = None,
    child_size: int | None = None,
    overlap: int | None = None,
) -> list[ChunkResult]:
    """Split text into hierarchical parent + child chunks."""
    ps = parent_size or settings.parent_chunk_size
    cs = child_size or settings.child_chunk_size
    ov = overlap or settings.child_chunk_overlap

    parent_texts = _split_at_boundaries(text, ps)
    results: list[ChunkResult] = []
    child_idx = 0

    for p_text, p_start in parent_texts:
        parent_id = uuid4()
        parent_chunk = ChunkResult(
            id=parent_id,
            parent_id=None,
            original_text=p_text,
            chunk_index=len(results),
            char_start=p_start,
            char_end=p_start + len(p_text),
            is_parent=True,
        )
        results.append(parent_chunk)

        children = _sliding_window(p_text, cs, ov, offset=p_start)
        for c_text, c_start in children:
            results.append(ChunkResult(
                id=uuid4(),
                parent_id=parent_id,
                original_text=c_text,
                chunk_index=child_idx,
                char_start=c_start,
                char_end=c_start + len(c_text),
                is_parent=False,
            ))
            child_idx += 1

    return results


async def add_contextual_text(
    chunks: list[ChunkResult],
    document_text: str,
) -> list[ChunkResult]:
    """
    Generate 50-100 word context for each child chunk using the context LLM.
    Uses Anthropic prompt caching when provider=claude: the document body is
    sent once and cached across all chunk calls for this document.
    """
    if not settings.contextual_retrieval_enabled:
        return chunks

    context_llm = get_context_llm()
    child_chunks = [c for c in chunks if not c.is_parent]

    use_cache = (
        settings.context_llm_use_prompt_caching
        and settings.context_llm_provider == "claude"
        and isinstance(context_llm, ClaudeClient)
    )

    for chunk in child_chunks:
        if use_cache:
            # Document body is marked ephemeral → cached across all chunks from same file
            resp = await context_llm.complete_with_cache(
                system=CONTEXTUAL_RETRIEVAL_SYSTEM,
                cached_prefix=f"<document>{document_text}</document>",
                user=f"<chunk>{chunk.original_text}</chunk>\nGive a short succinct context (50-100 words) situating this chunk within the overall document for retrieval purposes. Answer only with the context, no preamble.",
                max_tokens=150,
            )
        else:
            resp = await context_llm.complete(
                system=CONTEXTUAL_RETRIEVAL_SYSTEM,
                user=CONTEXT_PROMPT_TEMPLATE.format(
                    document_text=document_text[:8000],
                    chunk_text=chunk.original_text,
                ),
                max_tokens=150,
            )
        context = resp.text.strip()
        chunk.contextualized_text = context + "\n\n" + chunk.original_text

    return chunks


def _split_at_boundaries(text: str, max_size: int) -> list[tuple[str, int]]:
    """Split text into sections up to max_size, preferring paragraph/heading breaks."""
    if len(text) <= max_size:
        return [(text, 0)]

    results: list[tuple[str, int]] = []
    pos = 0
    while pos < len(text):
        end = min(pos + max_size, len(text))
        if end < len(text):
            # Try to break at double newline (paragraph)
            break_at = text.rfind("\n\n", pos, end)
            if break_at == -1 or break_at <= pos:
                # Fall back to single newline
                break_at = text.rfind("\n", pos, end)
            if break_at == -1 or break_at <= pos:
                break_at = end
            else:
                break_at += 1
        else:
            break_at = end
        chunk_text = text[pos:break_at].strip()
        if chunk_text:
            results.append((chunk_text, pos))
        pos = break_at
    return results


def _sliding_window(text: str, size: int, overlap: int, offset: int = 0) -> list[tuple[str, int]]:
    results: list[tuple[str, int]] = []
    pos = 0
    while pos < len(text):
        end = min(pos + size, len(text))
        chunk = text[pos:end].strip()
        if chunk:
            results.append((chunk, offset + pos))
        if end >= len(text):
            break
        pos += size - overlap
    return results
