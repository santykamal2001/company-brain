"""
Query router: classify a question as vector | graph | hybrid | decision.
Heuristic pre-filter handles obvious cases without an LLM call.
Ambiguous cases go to a cheap LLM classification call.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from llm.adapter import get_extraction_llm
from llm.prompts import QUERY_ROUTING_SYSTEM

# Patterns that strongly imply graph/relational queries
_GRAPH_PATTERNS = re.compile(
    r"\b(who works on|who is on|team members|org chart|reports to|manages|"
    r"both .* and |across departments|all people|everyone on|"
    r"which (team|department|project)|involved in|connected to|"
    r"works with|collaborates with|history of)\b",
    re.IGNORECASE,
)

# Patterns that imply Decision Trail queries
_DECISION_PATTERNS = re.compile(
    r"\b(why (do|did|are|is|was|were)|who decided|who approved|"
    r"reason (we|they|the team)|rationale (for|behind)|"
    r"how did we (end up|decide|choose)|what alternatives|"
    r"chose .* over|switched from|moved from|why not|history of the decision|"
    r"decided to)\b",
    re.IGNORECASE,
)

ROUTING_PROMPT = """\
Question: {question}

Classify the retrieval strategy. Output JSON only:
{{"mode": "vector|graph|hybrid|decision", "entities_mentioned": ["name1"]}}
"""


@dataclass
class RouteResult:
    mode: str  # vector | graph | hybrid | decision
    entities_mentioned: list[str] = field(default_factory=list)


async def classify(question: str) -> RouteResult:
    """Classify the query. Heuristics first; LLM fallback for ambiguous cases."""

    # Fast heuristic: decision keywords
    if _DECISION_PATTERNS.search(question):
        return RouteResult(mode="decision", entities_mentioned=_extract_names(question))

    # Fast heuristic: relational/graph keywords
    if _GRAPH_PATTERNS.search(question):
        return RouteResult(mode="hybrid", entities_mentioned=_extract_names(question))

    # LLM classification for ambiguous queries
    try:
        llm = get_extraction_llm()
        result = await llm.complete_json(
            system=QUERY_ROUTING_SYSTEM,
            user=ROUTING_PROMPT.format(question=question),
            max_tokens=100,
        )
        if isinstance(result, dict) and "mode" in result:
            mode = result["mode"]
            if mode not in ("vector", "graph", "hybrid", "decision"):
                mode = "vector"
            return RouteResult(
                mode=mode,
                entities_mentioned=list(result.get("entities_mentioned") or []),
            )
    except Exception:
        pass

    return RouteResult(mode="vector")


def _extract_names(question: str) -> list[str]:
    """
    Simple heuristic: extract capitalized multi-word names.
    Graph retrieval anchors on these for entity lookup.
    """
    tokens = question.split()
    names: list[str] = []
    current: list[str] = []
    for token in tokens:
        clean = re.sub(r"[^A-Za-z'-]", "", token)
        if clean and clean[0].isupper() and len(clean) > 1:
            current.append(clean)
        else:
            if len(current) >= 2:
                names.append(" ".join(current))
            elif current:
                names.append(current[0])
            current = []
    if current:
        names.append(" ".join(current))
    return list(dict.fromkeys(names))[:10]
