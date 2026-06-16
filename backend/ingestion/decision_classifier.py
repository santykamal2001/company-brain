"""
Decision classifier: detects organizational decisions in indexed chunks.
Creates Decision nodes in the AGE graph when confidence >= 0.75.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from llm.adapter import get_extraction_llm
from llm.prompts import DECISION_CLASSIFICATION_SYSTEM

BATCH_SIZE = 8

DECISION_PROMPT = """\
Analyze these content chunks. For each chunk, determine if it records a decision, conclusion, or resolution.

Chunks:
{chunks_text}

A decision is: a record of a choice made, conclusion reached, or resolution agreed upon.
Examples: "We decided to use PostgreSQL", "The team agreed to delay launch", "Leadership approved the reorg".
NOT a decision: general information, meeting agendas, status updates without resolution.

Output JSON array, one entry per chunk in the same order:
[
  {{
    "chunk_index": 0,
    "is_decision": true,
    "confidence": 0.92,
    "what_decided": "string (1-2 sentences)",
    "who_decided": ["name1", "name2"],
    "when_decided": "date string or null",
    "alternatives_considered": ["alternative1", "alternative2"],
    "supersedes": "description of prior state this decision replaces, or null"
  }}
]
"""


@dataclass
class DetectedDecision:
    chunk_index: int
    chunk_id: str
    confidence: float
    what_decided: str
    who_decided: list[str] = field(default_factory=list)
    when_decided: str | None = None
    alternatives_considered: list[str] = field(default_factory=list)
    supersedes: str | None = None


async def classify_chunks(
    chunk_texts: list[tuple[str, str]],  # (chunk_id, text)
) -> list[DetectedDecision]:
    """
    Returns detected decisions with confidence >= 0.75.
    chunk_texts is a list of (chunk_id, contextualized_text_or_original_text).
    """
    llm = get_extraction_llm()
    decisions: list[DetectedDecision] = []

    for batch_start in range(0, len(chunk_texts), BATCH_SIZE):
        batch = chunk_texts[batch_start : batch_start + BATCH_SIZE]
        chunks_text = "\n\n---\n\n".join(
            f"[Chunk {i}]:\n{text}" for i, (_, text) in enumerate(batch)
        )
        prompt = DECISION_PROMPT.format(chunks_text=chunks_text)

        try:
            result = await llm.complete_json(DECISION_CLASSIFICATION_SYSTEM, prompt, max_tokens=2000)
        except (ValueError, Exception):
            continue

        if not isinstance(result, list):
            continue

        for item in result:
            if not isinstance(item, dict):
                continue
            confidence = float(item.get("confidence", 0))
            if not item.get("is_decision") or confidence < 0.75:
                continue
            idx = int(item.get("chunk_index", 0))
            if idx >= len(batch):
                continue
            chunk_id = batch[idx][0]
            decisions.append(DetectedDecision(
                chunk_index=batch_start + idx,
                chunk_id=chunk_id,
                confidence=confidence,
                what_decided=str(item.get("what_decided", "")).strip(),
                who_decided=list(item.get("who_decided") or []),
                when_decided=item.get("when_decided"),
                alternatives_considered=list(item.get("alternatives_considered") or []),
                supersedes=item.get("supersedes"),
            ))

    return decisions
