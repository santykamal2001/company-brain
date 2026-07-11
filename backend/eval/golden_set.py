"""
Golden Q&A set for Company Brain evaluation.

Question categories:
  fact          — simple single-document fact lookup
  decision      — decision trail (why/who decided)
  graph         — multi-hop relational (graph traversal)
  unanswerable  — NO answer exists in the corpus; correct response is refusal/IDK
  adversarial   — probes for hallucination of plausible-but-wrong facts
  multi_hop     — complex cross-document reasoning requiring ≥2 hops

For `unanswerable` and `adversarial` groups, set expected="<REFUSE>" to signal
that the evaluator should score refusal as correct and a confident specific answer
as a hallucination (score=0).
"""
from __future__ import annotations

import json
from pathlib import Path

GOLDEN_SET_PATH = Path(__file__).parent / "golden_qa.json"

REFUSE_SENTINEL = "<REFUSE>"

_DEFAULT: list[dict] = [
    # ─── GROUP: fact — simple retrieval ─────────────────────────────────────
    {"id": "q01", "question": "Who is the CTO of NovaTech?",
     "expected": "Daniel Okafor", "mode": "vector", "group": "fact"},

    {"id": "q02", "question": "Who leads the Platform team?",
     "expected": "James Chen", "mode": "vector", "group": "fact"},

    {"id": "q03", "question": "What is Project Nova about?",
     "expected": "AI answer quality", "mode": "vector", "group": "fact"},

    {"id": "q04", "question": "What is NovaTech's ARR as of Q2 2026?",
     "expected": "$1.2M", "mode": "vector", "group": "fact"},

    {"id": "q05", "question": "Who wrote the notes for the Q2 all-hands?",
     "expected": "Grace Kimura", "mode": "vector", "group": "fact"},

    {"id": "q06", "question": "How many employees does NovaTech have?",
     "expected": "47", "mode": "vector", "group": "fact"},

    {"id": "q07", "question": "What is the target ARR for Q4 2026?",
     "expected": "$2.4M", "mode": "vector", "group": "fact"},

    {"id": "q08", "question": "When was the Q2 all-hands meeting held?",
     "expected": "June 2026", "mode": "vector", "group": "fact"},

    {"id": "q09", "question": "What role does Fatima Al-Rashid hold?",
     "expected": "Security and Compliance Lead", "mode": "vector", "group": "fact"},

    {"id": "q10", "question": "What is the standard notice period mentioned in the HR policies?",
     "expected": "4 weeks", "mode": "vector", "group": "fact"},

    # ─── GROUP: decision — decision trail ───────────────────────────────────
    {"id": "q11", "question": "Why do we use PostgreSQL instead of MongoDB?",
     "expected": "ACID, AGE graph extension, team expertise",
     "mode": "decision", "group": "decision"},

    {"id": "q12", "question": "Why did we build our own LLM adapter instead of using LangChain?",
     "expected": "LangChain had too many dependencies",
     "mode": "decision", "group": "decision"},

    {"id": "q13", "question": "Why do we use local embeddings instead of OpenAI?",
     "expected": "Cost, data sovereignty, BGE-large MTEB performance",
     "mode": "decision", "group": "decision"},

    {"id": "q14", "question": "Why did we choose Qdrant over Pinecone?",
     "expected": "Self-hosted, native BM25 hybrid, rich payload filtering",
     "mode": "decision", "group": "decision"},

    {"id": "q15", "question": "Why did we switch from Kuzu to Apache AGE for the knowledge graph?",
     "expected": "Kuzu was archived Oct 2025; AGE runs inside Postgres, no extra container",
     "mode": "decision", "group": "decision"},

    {"id": "q16", "question": "What was the rationale for choosing Celery over other task queues?",
     "expected": "Redis, retries, existing team familiarity",
     "mode": "decision", "group": "decision"},

    # ─── GROUP: graph — multi-hop relational ────────────────────────────────
    {"id": "q17", "question": "Who works on both Project Titan and the Platform team?",
     "expected": "James Chen", "mode": "hybrid", "group": "graph"},

    {"id": "q18", "question": "Which engineers report to Aisha Johnson?",
     "expected": "Ryan Park, Elena Vasquez, Nate Wilson, Priyanka Desai",
     "mode": "hybrid", "group": "graph"},

    {"id": "q19", "question": "Who is responsible for the EMEA expansion?",
     "expected": "Brandon Clark", "mode": "hybrid", "group": "graph"},

    {"id": "q20", "question": "What projects is Sophia Nguyen involved in?",
     "expected": "Project Nova", "mode": "hybrid", "group": "graph"},

    {"id": "q21", "question": "Who is handling the SOC 2 compliance work?",
     "expected": "Fatima Al-Rashid", "mode": "hybrid", "group": "graph"},

    {"id": "q22", "question": "Which team is Daniel Okafor part of?",
     "expected": "Leadership / Executive", "mode": "hybrid", "group": "graph"},

    # ─── GROUP: multi_hop — cross-document complex reasoning ────────────────
    {"id": "q23",
     "question": "Who manages the engineers working on Project Nova and what team are they in?",
     "expected": "Aisha Johnson manages engineers; they are in the Engineering team",
     "mode": "hybrid", "group": "multi_hop"},

    {"id": "q24",
     "question": "What technology decisions did NovaTech make and who approved them?",
     "expected": "PostgreSQL, Qdrant, AGE, local embeddings; decisions attributed to engineering leadership",
     "mode": "hybrid", "group": "multi_hop"},

    {"id": "q25",
     "question": "What were the Q2 2026 revenue results and who presented them at the all-hands?",
     "expected": "$1.2M ARR; presented at all-hands by leadership",
     "mode": "hybrid", "group": "multi_hop"},

    {"id": "q26",
     "question": "Which people are in both the Engineering team and working on a Q3 project?",
     "expected": "Engineers on Q3 roadmap projects",
     "mode": "hybrid", "group": "multi_hop"},

    {"id": "q27",
     "question": "What is the salary band for a Senior Engineer and what are NovaTech's bonus rules?",
     "expected": "salary band and bonus policy from HR doc",
     "mode": "vector", "group": "multi_hop"},

    # ─── GROUP: unanswerable — correct answer is to refuse ──────────────────
    # The model should say 'I don't know' / 'I don't have information' / similar.
    # A specific confident answer means hallucination.
    {"id": "q28",
     "question": "What is NovaTech's Series B valuation?",
     "expected": REFUSE_SENTINEL,
     "mode": "vector", "group": "unanswerable"},

    {"id": "q29",
     "question": "Who is NovaTech's Chief Marketing Officer?",
     "expected": REFUSE_SENTINEL,
     "mode": "vector", "group": "unanswerable"},

    {"id": "q30",
     "question": "What is the contract value with Acme Corp?",
     "expected": REFUSE_SENTINEL,
     "mode": "vector", "group": "unanswerable"},

    {"id": "q31",
     "question": "When did NovaTech file its first patent?",
     "expected": REFUSE_SENTINEL,
     "mode": "vector", "group": "unanswerable"},

    {"id": "q32",
     "question": "What is the NovaTech board's compensation package?",
     "expected": REFUSE_SENTINEL,
     "mode": "vector", "group": "unanswerable"},

    {"id": "q33",
     "question": "How many users does NovaTech's product have?",
     "expected": REFUSE_SENTINEL,
     "mode": "vector", "group": "unanswerable"},

    {"id": "q34",
     "question": "What is the name of NovaTech's largest customer?",
     "expected": REFUSE_SENTINEL,
     "mode": "vector", "group": "unanswerable"},

    {"id": "q35",
     "question": "What is NovaTech's net promoter score?",
     "expected": REFUSE_SENTINEL,
     "mode": "vector", "group": "unanswerable"},

    # ─── GROUP: adversarial — probes for hallucination of plausible facts ───
    # These look like they should be in the corpus but the specific detail is wrong or absent.
    {"id": "q36",
     "question": "What is the exact base salary for a Staff Engineer at NovaTech?",
     "expected": REFUSE_SENTINEL,  # exact salary not stored; model should give band not invent number
     "mode": "vector", "group": "adversarial"},

    {"id": "q37",
     "question": "Who was the previous CTO before Daniel Okafor?",
     "expected": REFUSE_SENTINEL,
     "mode": "vector", "group": "adversarial"},

    {"id": "q38",
     "question": "Why did NovaTech switch from AWS to Google Cloud?",
     "expected": REFUSE_SENTINEL,  # no such switch mentioned
     "mode": "decision", "group": "adversarial"},

    {"id": "q39",
     "question": "What did NovaTech decide about Kubernetes vs Docker Swarm?",
     "expected": REFUSE_SENTINEL,  # not in documents
     "mode": "decision", "group": "adversarial"},

    {"id": "q40",
     "question": "Who is the head of the Sales team?",
     "expected": REFUSE_SENTINEL,  # no Sales team in docs
     "mode": "vector", "group": "adversarial"},

    {"id": "q41",
     "question": "What is NovaTech's annual churn rate?",
     "expected": REFUSE_SENTINEL,
     "mode": "vector", "group": "adversarial"},

    {"id": "q42",
     "question": "When did Ryan Park join NovaTech?",
     "expected": REFUSE_SENTINEL,  # join dates not in docs
     "mode": "vector", "group": "adversarial"},

    {"id": "q43",
     "question": "What is the Q3 2026 headcount target for the Sales team?",
     "expected": REFUSE_SENTINEL,  # no Sales headcount target
     "mode": "vector", "group": "adversarial"},
]


def load_golden_set() -> list[dict]:
    if GOLDEN_SET_PATH.exists():
        with GOLDEN_SET_PATH.open() as f:
            return json.load(f)
    return list(_DEFAULT)


def save_golden_set(items: list[dict]) -> None:
    with GOLDEN_SET_PATH.open("w") as f:
        json.dump(items, f, indent=2)


def add_item(
    question: str,
    expected: str,
    mode: str = "vector",
    group: str = "fact",
) -> dict:
    items = load_golden_set()
    item = {
        "id": f"q{len(items)+1:02d}",
        "question": question,
        "expected": expected,
        "mode": mode,
        "group": group,
    }
    items.append(item)
    save_golden_set(items)
    return item


def is_refuse_question(item: dict) -> bool:
    return item.get("expected") == REFUSE_SENTINEL
