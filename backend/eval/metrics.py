"""
Retrieval and answer quality metrics.
- Recall@k, NDCG@k, MRR  — offline; need relevance judgements
- llm_judge              — online; Claude Haiku rates answer quality 1-5
"""
from __future__ import annotations

import math


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


async def llm_judge(question: str, answer: str, expected: str) -> float:
    """
    Ask Claude Haiku to rate how well the answer covers the expected key facts.
    Returns a float 0.0–1.0 (maps 1-5 integer score).
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
        # If LLM judge fails, fall back to keyword heuristic
        return _keyword_score(answer, expected)


def _keyword_score(answer: str, expected: str) -> float:
    """Fallback: what fraction of expected keywords appear in the answer."""
    keywords = [w.strip(".,;") for w in expected.lower().split() if len(w) > 3]
    if not keywords:
        return 0.0
    hits = sum(1 for kw in keywords if kw in answer.lower())
    return hits / len(keywords)
