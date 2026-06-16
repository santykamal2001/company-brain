"""
Entity resolution: merges near-duplicate entity names before graph upsert.
Step 1: deterministic normalize (lowercase, strip punctuation, trim)
Step 2: lookup existing nodes in AGE graph
Step 3: LLM-assisted fuzzy merge for remaining ambiguous near-matches
"""
from __future__ import annotations

import re
import unicodedata

from ingestion.extractor_graph import ExtractedEntity

# Minimum string similarity to trigger LLM disambiguation check
FUZZY_THRESHOLD = 0.75


def normalize(name: str) -> str:
    """Canonical form for deduplication lookups."""
    name = unicodedata.normalize("NFC", name)
    name = re.sub(r"[^\w\s]", "", name)
    return re.sub(r"\s+", " ", name).strip().lower()


def deduplicate_within_batch(entities: list[ExtractedEntity]) -> list[ExtractedEntity]:
    """
    Remove exact duplicates (after normalization) within a single extraction batch.
    Keeps the first occurrence; merges descriptions.
    """
    seen: dict[str, ExtractedEntity] = {}
    for entity in entities:
        key = normalize(entity.name)
        if key in seen:
            existing = seen[key]
            if entity.description and entity.description not in existing.description:
                existing.description = (existing.description + " " + entity.description).strip()
        else:
            seen[key] = entity
    return list(seen.values())


def jaccard_similarity(a: str, b: str) -> float:
    tokens_a = set(a.lower().split())
    tokens_b = set(b.lower().split())
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


def find_merge_candidates(
    new_entities: list[ExtractedEntity],
    existing_names: list[str],
) -> list[tuple[ExtractedEntity, str]]:
    """
    Returns (new_entity, existing_name) pairs that are potential duplicates
    (jaccard >= FUZZY_THRESHOLD but not exact normalized match).
    """
    candidates = []
    for entity in new_entities:
        norm_new = normalize(entity.name)
        for existing in existing_names:
            norm_existing = normalize(existing)
            if norm_new == norm_existing:
                # Exact match — handled by caller
                continue
            sim = jaccard_similarity(norm_new, norm_existing)
            if sim >= FUZZY_THRESHOLD:
                candidates.append((entity, existing))
    return candidates
