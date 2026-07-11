"""
Golden Q&A set: load, save, and seed from EVALUATION_GUIDE.md test cases.
All 15 evaluable questions from the 6 test groups are pre-seeded.
"""
from __future__ import annotations

import json
from pathlib import Path

GOLDEN_SET_PATH = Path(__file__).parent / "golden_qa.json"

# Pre-seeded from test_data/EVALUATION_GUIDE.md
_DEFAULT: list[dict] = [
    # GROUP 1 — Simple Fact Retrieval (vector mode expected)
    {"id": "q01", "question": "Who is the CTO of NovaTech?",                    "expected": "Daniel Okafor",              "mode": "vector",   "group": "fact"},
    {"id": "q02", "question": "Who leads the Platform team?",                   "expected": "James Chen",                 "mode": "vector",   "group": "fact"},
    {"id": "q03", "question": "What is Project Nova about?",                    "expected": "AI answer quality",          "mode": "vector",   "group": "fact"},
    {"id": "q04", "question": "What is NovaTech's ARR as of Q2 2026?",          "expected": "$1.2M",                      "mode": "vector",   "group": "fact"},
    {"id": "q05", "question": "Who wrote the notes for the Q2 all-hands?",      "expected": "Grace Kimura",               "mode": "vector",   "group": "fact"},
    # GROUP 2 — Decision Trail (decision mode expected)
    {"id": "q06", "question": "Why do we use PostgreSQL instead of MongoDB?",                                    "expected": "ACID, AGE graph extension, team expertise",                          "mode": "decision", "group": "decision"},
    {"id": "q07", "question": "Why did we build our own LLM adapter instead of using LangChain?",               "expected": "LangChain had too many dependencies",                                "mode": "decision", "group": "decision"},
    {"id": "q08", "question": "Why do we use local embeddings instead of OpenAI?",                              "expected": "Cost, data sovereignty, BGE-large MTEB performance",                  "mode": "decision", "group": "decision"},
    {"id": "q09", "question": "Why did we choose Qdrant over Pinecone?",                                        "expected": "Self-hosted, native BM25 hybrid, rich payload filtering",             "mode": "decision", "group": "decision"},
    {"id": "q10", "question": "Why did we switch from Kuzu to Apache AGE for the knowledge graph?",            "expected": "Kuzu was archived Oct 2025; AGE runs inside Postgres, no extra container", "mode": "decision", "group": "decision"},
    # GROUP 3 — Multi-hop Relational (hybrid/graph mode expected)
    {"id": "q11", "question": "Who works on both Project Titan and the Platform team?",     "expected": "James Chen",           "mode": "hybrid", "group": "graph"},
    {"id": "q12", "question": "Which engineers report to Aisha Johnson?",                  "expected": "Ryan Park, Elena Vasquez, Nate Wilson, Priyanka Desai", "mode": "hybrid", "group": "graph"},
    {"id": "q13", "question": "Who is responsible for the EMEA expansion?",               "expected": "Brandon Clark",         "mode": "hybrid", "group": "graph"},
    {"id": "q14", "question": "What projects is Sophia Nguyen involved in?",              "expected": "Project Nova",          "mode": "hybrid", "group": "graph"},
    {"id": "q15", "question": "Who is handling the SOC 2 compliance work?",               "expected": "Fatima Al-Rashid",      "mode": "hybrid", "group": "graph"},
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
