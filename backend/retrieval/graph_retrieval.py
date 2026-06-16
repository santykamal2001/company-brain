from __future__ import annotations

from retrieval.graph_store import query_decisions, traverse


async def get_graph_context(
    entity_names: list[str],
    acl_roles: list[str],
    mode: str,
    token_budget: int | None = None,
) -> list[str]:
    """Fetch graph context appropriate for the query mode."""
    if not entity_names and mode not in ("decision",):
        return []

    triples = await traverse(
        entity_names=entity_names,
        acl_roles=acl_roles,
        depth=1,
        token_budget=token_budget,
    )
    return triples


async def get_decision_context(
    topic: str = "",
    project: str = "",
    limit: int = 10,
) -> list[dict]:
    return await query_decisions(topic=topic, project=project, limit=limit)


def format_graph_triples(triples: list[str]) -> str:
    if not triples:
        return ""
    return "\n".join(triples)


def format_decisions(decisions: list[dict]) -> str:
    if not decisions:
        return ""
    lines = []
    for d in decisions:
        raw = d.get("raw", "")
        lines.append(f"Decision: {raw}")
    return "\n".join(lines)
