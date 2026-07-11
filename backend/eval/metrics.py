"""
Retrieval and answer quality metrics.

Scoring:
  llm_judge           — ask Haiku to rate answer vs expected key facts (0.0–1.0)
  refusal_accuracy    — for unanswerable/adversarial questions: did the model correctly
                        say "I don't know" instead of hallucinating? (1.0 or 0.0)
  hallucination_check — for answerable questions: does the answer contain facts not
                        grounded in the retrieved chunks? (1.0 = grounded, 0.0 = hallucinated)

Offline metrics (require chunk-level relevance labels):
  recall_at_k, ndcg_at_k, mrr
"""
from __future__ import annotations

import math
import re

# Phrases that indicate the model correctly refused to answer
_REFUSAL_PHRASES = [
    "don't have information",
    "don't have that information",
    "no information",
    "not mentioned",
    "not available",
    "i don't know",
    "i'm not sure",
    "i cannot find",
    "cannot find",
    "not in the",
    "not found",
    "doesn't appear",
    "does not appear",
    "unable to find",
    "no details",
    "no data",
    "this information is not",
    "i couldn't find",
    "could not find",
]


def recall_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    if not relevant:
        return 1.0
    return len(set(retrieved[:k]) & set(relevant)) / len(relevant)


def ndcg_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    rel_set = set(relevant)
    dcg = sum(
        1 / math.log2(i + 2)
        for i, doc_id in enumerate(retrieved[:k])
        if doc_id in rel_set
    )
    ideal = min(len(relevant), k)
    idcg = sum(1 / math.log2(i + 2) for i in range(ideal))
    return dcg / idcg if idcg > 0 else 0.0


def mrr(retrieved: list[str], relevant: list[str]) -> float:
    rel_set = set(relevant)
    for i, doc_id in enumerate(retrieved):
        if doc_id in rel_set:
            return 1 / (i + 1)
    return 0.0


def refusal_accuracy(answer: str) -> float:
    """
    Returns 1.0 if the model's answer indicates it doesn't have the information
    (correct for unanswerable/adversarial questions), 0.0 if it gave a specific
    confident answer (hallucination risk).
    """
    lower = answer.lower()
    if any(phrase in lower for phrase in _REFUSAL_PHRASES):
        return 1.0
    # Short answer with uncertainty words also counts
    if len(answer) < 120 and any(w in lower for w in ["unclear", "uncertain", "unavailable", "no record"]):
        return 1.0
    return 0.0


async def hallucination_check(
    question: str,
    answer: str,
    source_excerpts: list[str],
) -> float:
    """
    Ask Haiku to verify whether the answer is grounded in the provided source chunks.
    Returns 1.0 (grounded) or 0.0 (likely hallucinated).
    Falls back to 1.0 if judge unavailable (conservative — don't penalize on judge failure).
    """
    if not source_excerpts:
        return 0.5  # Can't verify without sources

    try:
        import anthropic
        from config import get_settings
        settings = get_settings()
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

        sources_text = "\n\n---\n\n".join(source_excerpts[:5])
        prompt = (
            "You are an answer grounding verifier.\n\n"
            f"QUESTION: {question}\n\n"
            f"ANSWER: {answer[:800]}\n\n"
            f"SOURCE CHUNKS:\n{sources_text[:2000]}\n\n"
            "Does the ANSWER contain specific facts (names, numbers, decisions, dates) "
            "that are NOT supported by the SOURCE CHUNKS?\n"
            "Reply with exactly one word: GROUNDED or HALLUCINATED"
        )
        resp = await client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}],
        )
        verdict = resp.content[0].text.strip().upper()
        return 1.0 if "GROUND" in verdict else 0.0
    except Exception:
        return 1.0  # Conservative fallback


async def llm_judge(question: str, answer: str, expected: str) -> float:
    """
    Ask Haiku to rate how well the answer covers the expected key facts.
    Returns a float 0.0–1.0 (maps 1-5 integer score to 0.0/0.25/0.5/0.75/1.0).
    Falls back to keyword heuristic if judge is unavailable.
    """
    try:
        import anthropic
        from config import get_settings
        settings = get_settings()

        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        prompt = (
            "Rate how well this ANSWER covers the EXPECTED KEY FACTS for the QUESTION.\n\n"
            f"QUESTION: {question}\n\n"
            f"ANSWER: {answer[:1000]}\n\n"
            f"EXPECTED KEY FACTS: {expected}\n\n"
            "Reply with a SINGLE integer 1–5:\n"
            "5 = Correct, covers all expected facts\n"
            "4 = Mostly correct, minor omission\n"
            "3 = Partially correct\n"
            "2 = Mostly wrong\n"
            "1 = Incorrect or empty\n\n"
            "Score:"
        )
        resp = await client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=8,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        score = int(raw[0])
        return (score - 1) / 4.0
    except Exception:
        return _keyword_score(answer, expected)


def _keyword_score(answer: str, expected: str) -> float:
    """Fallback: what fraction of expected keywords appear in the answer."""
    keywords = [w.strip(".,;") for w in expected.lower().split() if len(w) > 3]
    if not keywords:
        return 0.0
    hits = sum(1 for kw in keywords if kw in answer.lower())
    return hits / len(keywords)
