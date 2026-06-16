"""
LLM-based entity and relation extraction via forced tool-use (structured output).
Feeds contextualized_text (not original_text) so the LLM has full situating context.
Batches 3-5 child chunks per call to reduce latency.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from llm.adapter import get_extraction_llm
from llm.prompts import ENTITY_EXTRACTION_SYSTEM

BATCH_SIZE = 4

EXTRACTION_PROMPT = """\
Extract entities and relationships from these document chunks.

Chunks:
{chunks_text}

Output JSON with this exact schema:
{{
  "entities": [
    {{"name": "string", "type": "Person|Team|Project|Topic|Process|Asset|Location|Event", "description": "string"}}
  ],
  "relations": [
    {{"source": "entity_name", "target": "entity_name", "rel_type": "string", "description": "string"}}
  ]
}}

Rules:
- Only extract entities clearly and explicitly mentioned, not inferred
- For rel_type use: WORKS_ON, PART_OF, OWNS, AUTHORED, DISCUSSED_IN, TAGGED_WITH, DEPENDS_ON, INVOLVES, or a descriptive verb
- Canonical names only (full name for Person, not pronouns)
- Skip entities with no clear identity (e.g., "someone", "they")
"""


@dataclass
class ExtractedEntity:
    name: str
    type: str
    description: str = ""


@dataclass
class ExtractedRelation:
    source: str
    target: str
    rel_type: str
    description: str = ""


@dataclass
class ExtractionResult:
    entities: list[ExtractedEntity] = field(default_factory=list)
    relations: list[ExtractedRelation] = field(default_factory=list)


async def extract_from_chunks(chunk_texts: list[str]) -> ExtractionResult:
    """Extract entities/relations from a list of (contextualized) chunk texts."""
    llm = get_extraction_llm()
    all_entities: list[ExtractedEntity] = []
    all_relations: list[ExtractedRelation] = []
    seen_entity_names: set[str] = set()

    for i in range(0, len(chunk_texts), BATCH_SIZE):
        batch = chunk_texts[i : i + BATCH_SIZE]
        chunks_text = "\n\n---\n\n".join(
            f"[Chunk {i + j + 1}]:\n{text}" for j, text in enumerate(batch)
        )
        prompt = EXTRACTION_PROMPT.format(chunks_text=chunks_text)

        try:
            result = await llm.complete_json(ENTITY_EXTRACTION_SYSTEM, prompt, max_tokens=1500)
        except (ValueError, Exception):
            continue

        if not isinstance(result, dict):
            continue

        for e in result.get("entities", []):
            name = (e.get("name") or "").strip()
            etype = (e.get("type") or "").strip()
            if name and etype and name.lower() not in seen_entity_names:
                seen_entity_names.add(name.lower())
                all_entities.append(ExtractedEntity(
                    name=name,
                    type=etype,
                    description=(e.get("description") or "").strip(),
                ))

        for r in result.get("relations", []):
            src = (r.get("source") or "").strip()
            tgt = (r.get("target") or "").strip()
            rel = (r.get("rel_type") or "").strip()
            if src and tgt and rel:
                all_relations.append(ExtractedRelation(
                    source=src,
                    target=tgt,
                    rel_type=rel,
                    description=(r.get("description") or "").strip(),
                ))

    return ExtractionResult(entities=all_entities, relations=all_relations)
