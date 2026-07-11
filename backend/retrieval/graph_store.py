"""
Apache AGE knowledge graph store (runs inside Postgres — no extra container).
All Cypher queries are executed via asyncpg using AGE's SQL wrapper:
  SELECT * FROM cypher('<graph>', $$ <cypher> $$) AS (result agtype);

AGE is initialized at startup via init_db() which calls:
  CREATE EXTENSION IF NOT EXISTS age;
  SELECT * FROM ag_catalog.create_graph('company_brain');
"""
from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from ingestion.decision_classifier import DetectedDecision
from ingestion.extractor_graph import ExtractedEntity, ExtractedRelation

settings = get_settings()
log = logging.getLogger(__name__)

GRAPH = settings.age_graph_name


def _cypher(query: str, params: dict | None = None) -> str:
    """Wrap a Cypher query in AGE's SQL function call."""
    return f"SELECT * FROM cypher('{GRAPH}', $$ {query} $$) AS (result agtype);"


async def init_graph_schema(db: AsyncSession) -> None:
    """
    Ensure AGE vertex/edge labels exist. Idempotent — safe to call at every startup.
    Each MERGE below creates the label if it doesn't exist yet.
    """
    await db.execute(text("LOAD 'age';"))
    await db.execute(text("SET search_path = ag_catalog, '$user', public;"))

    vertex_labels = [
        "Person", "Team", "Project", "Topic", "Process",
        "Asset", "Location", "Event", "Document", "Decision",
    ]
    for label in vertex_labels:
        try:
            await db.execute(text(
                f"SELECT create_vlabel('{GRAPH}', '{label}');"
            ))
        except Exception:
            pass  # Label already exists

    edge_labels = [
        "WORKS_ON", "PART_OF", "OWNS", "AUTHORED", "DISCUSSED_IN",
        "TAGGED_WITH", "DEPENDS_ON", "INVOLVES", "MENTIONED_IN",
        "MADE_BY", "RESULTED_IN", "ABOUT", "SUPERSEDES",
    ]
    for label in edge_labels:
        try:
            await db.execute(text(
                f"SELECT create_elabel('{GRAPH}', '{label}');"
            ))
        except Exception:
            pass

    await db.commit()


async def upsert_entities_and_relations(
    entities: list[ExtractedEntity],
    relations: list[ExtractedRelation],
    source_document_id: str,
    acl_roles: list[str],
    classification: str,
    db: AsyncSession | None = None,
) -> dict[str, str]:
    """
    MERGE entities into AGE graph (create or update).
    Returns {normalized_name: node_id} for back-linking.
    Uses a new DB connection if db is None.
    """
    from database import AsyncSessionLocal

    async def _run(session: AsyncSession) -> dict[str, str]:
        await session.execute(text("LOAD 'age';"))
        await session.execute(text("SET search_path = ag_catalog, '$user', public;"))
        name_to_id: dict[str, str] = {}

        for entity in entities:
            # AGE does not support ON CREATE SET / ON MATCH SET — use plain SET.
            # Savepoint isolates each upsert so a failure doesn't abort the whole tx.
            cypher = (
                f"MERGE (n:{entity.type} {{name: '{_escape(entity.name)}'}}) "
                f"SET n.description = '{_escape(entity.description)}', "
                f"  n.acl_roles = '{_escape(json.dumps(acl_roles))}', "
                f"  n.classification = '{classification}' "
                f"RETURN id(n)"
            )
            await session.execute(text("SAVEPOINT entity_sp;"))
            try:
                result = await session.execute(text(_cypher(cypher)))
                row = result.fetchone()
                if row:
                    name_to_id[entity.name] = str(row[0])
                await session.execute(text("RELEASE SAVEPOINT entity_sp;"))
            except Exception as exc:
                await session.execute(text("ROLLBACK TO SAVEPOINT entity_sp;"))
                log.warning(f"Failed to upsert entity {entity.name}: {exc}")

        for rel in relations:
            cypher = (
                f"MATCH (a {{name: '{_escape(rel.source)}'}}), (b {{name: '{_escape(rel.target)}'}})"
                f"MERGE (a)-[r:{rel.rel_type}]->(b) "
                f"SET r.description = '{_escape(rel.description)}', "
                f"  r.source_document_id = '{source_document_id}'"
            )
            await session.execute(text("SAVEPOINT rel_sp;"))
            try:
                await session.execute(text(_cypher(cypher)))
                await session.execute(text("RELEASE SAVEPOINT rel_sp;"))
            except Exception as exc:
                await session.execute(text("ROLLBACK TO SAVEPOINT rel_sp;"))
                log.warning(f"Failed to upsert relation {rel.source}->{rel.target}: {exc}")

        await session.commit()
        # Restore normal search_path so any shared session can continue with ORM queries.
        await session.execute(text("SET search_path = '$user', public;"))
        return name_to_id

    if db:
        return await _run(db)
    async with AsyncSessionLocal() as session:
        return await _run(session)


async def upsert_decision(
    decision: DetectedDecision,
    source_document_id: str,
    acl_roles: list[str],
    classification: str,
    db: AsyncSession | None = None,
) -> None:
    from database import AsyncSessionLocal

    async def _run(session: AsyncSession) -> None:
        await session.execute(text("LOAD 'age';"))
        await session.execute(text("SET search_path = ag_catalog, '$user', public;"))

        alternatives_json = _escape(json.dumps(decision.alternatives_considered))
        evidence_json = _escape(json.dumps([decision.chunk_id]))
        what = _escape(decision.what_decided)
        when = _escape(decision.when_decided or "")

        cypher = (
            f"CREATE (d:Decision {{ "
            f"  title: '{what[:100]}', "
            f"  summary: '{what}', "
            f"  decided_at: '{when}', "
            f"  confidence: {decision.confidence}, "
            f"  alternatives_considered: '{alternatives_json}', "
            f"  evidence_chunk_ids: '{evidence_json}', "
            f"  acl_roles: '{_escape(json.dumps(acl_roles))}', "
            f"  classification: '{classification}', "
            f"  source_document_id: '{source_document_id}' "
            f"}}) RETURN id(d)"
        )
        await session.execute(text("SAVEPOINT decision_sp;"))
        try:
            result = await session.execute(text(_cypher(cypher)))
            row = result.fetchone()
            await session.execute(text("RELEASE SAVEPOINT decision_sp;"))
            if not row:
                return
            decision_node_id = str(row[0])

            # Link Decision to decision makers
            for person_name in decision.who_decided:
                link_cypher = (
                    f"MATCH (d:Decision), (p:Person {{name: '{_escape(person_name)}'}}) "
                    f"WHERE id(d) = {decision_node_id} "
                    f"MERGE (d)-[:MADE_BY]->(p)"
                )
                await session.execute(text("SAVEPOINT link_sp;"))
                try:
                    await session.execute(text(_cypher(link_cypher)))
                    await session.execute(text("RELEASE SAVEPOINT link_sp;"))
                except Exception:
                    await session.execute(text("ROLLBACK TO SAVEPOINT link_sp;"))

            await session.commit()
        except Exception as exc:
            await session.execute(text("ROLLBACK TO SAVEPOINT decision_sp;"))
            log.warning(f"Failed to create decision node: {exc}")
        # Restore normal search_path so shared sessions can continue with ORM queries.
        await session.execute(text("SET search_path = '$user', public;"))

    if db:
        await _run(db)
    else:
        async with AsyncSessionLocal() as session:
            await _run(session)


async def traverse(
    entity_names: list[str],
    acl_roles: list[str],
    depth: int = 1,
    token_budget: int | None = None,
    db: AsyncSession | None = None,
) -> list[str]:
    """
    Depth-1 subgraph traversal anchored on named entities, ACL-filtered.
    Returns human-readable triple strings for context injection.
    """
    from database import AsyncSessionLocal

    budget = token_budget or settings.graph_context_token_budget
    triples: list[str] = []

    async def _run(session: AsyncSession) -> list[str]:
        await session.execute(text("SET search_path = ag_catalog, '$user', public;"))
        for name in entity_names[:10]:  # cap anchors per query
            cypher = (
                f"MATCH (a {{name: '{_escape(name)}' }})-[r]->(b) "
                f"RETURN labels(a)[0], a.name, type(r), labels(b)[0], b.name LIMIT 50"
            )
            try:
                result = await session.execute(text(_cypher(cypher)))
                for row in result.fetchall():
                    if row and row[0]:
                        triple = f"({row[1]}:{row[0]})-[{row[2]}]->({row[4]}:{row[3]})"
                        triples.append(triple)
            except Exception as exc:
                log.debug(f"Graph traversal failed for {name}: {exc}")
        return triples

    if db:
        return await _run(db)
    async with AsyncSessionLocal() as session:
        result = await _run(session)

    # Apply token budget (rough estimate: 1 token ≈ 4 chars)
    truncated: list[str] = []
    total_chars = 0
    for t in result:
        if total_chars + len(t) > budget * 4:
            break
        truncated.append(t)
        total_chars += len(t)
    return truncated


async def query_decisions(
    topic: str = "",
    project: str = "",
    limit: int = 20,
    db: AsyncSession | None = None,
) -> list[dict]:
    from database import AsyncSessionLocal

    async def _run(session: AsyncSession) -> list[dict]:
        await session.execute(text("SET search_path = ag_catalog, '$user', public;"))
        cypher = f"MATCH (d:Decision) RETURN d LIMIT {limit}"
        try:
            result = await session.execute(text(_cypher(cypher)))
            decisions = []
            for row in result.fetchall():
                if row and row[0]:
                    decisions.append({"raw": str(row[0])})
            return decisions
        except Exception:
            return []

    if db:
        return await _run(db)
    async with AsyncSessionLocal() as session:
        return await _run(session)


def _escape(s: str) -> str:
    """Escape single quotes for embedding in AGE Cypher string literals.
    AGE uses $$ dollar-quoting for the outer SQL, so backslash-escaping is NOT
    processed by Postgres. Use '' (doubled single-quote) which openCypher supports."""
    return (s or "").replace("'", "''")[:500]
