"""
Celery tasks for background document ingestion.
Each document goes through: extract → chunk → contextualize → ACL classify →
embed+index (Qdrant) → entity extract → entity resolve → graph upsert →
decision classify → decision graph nodes.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import time
from pathlib import Path
from uuid import UUID

from celery import Celery

from config import get_settings

settings = get_settings()

app = Celery("company_brain", broker=settings.redis_url, backend=settings.redis_url)
app.conf.task_serializer = "json"
app.conf.result_serializer = "json"
app.conf.accept_content = ["json"]

# Celery beat: daily knowledge health check at 03:00 UTC
app.conf.beat_schedule = {
    "daily-health-check": {
        "task": "quality_monitor.run_health_check",
        "schedule": 86400,  # every 24h in seconds; replace with crontab(hour=3) for exact time
    },
}
app.conf.timezone = "UTC"

# Ensure quality_monitor tasks are discoverable by Celery
app.autodiscover_tasks(["ingestion"])

log = logging.getLogger(__name__)


def _file_hash(path: Path) -> str:
    h = hashlib.md5()
    size = path.stat().st_size
    with path.open("rb") as f:
        if size > 2 * 1024 * 1024:
            h.update(f.read(1024 * 1024))
            f.seek(-1024 * 1024, 2)
            h.update(f.read(1024 * 1024))
        else:
            h.update(f.read())
    return h.hexdigest()


def _make_worker_session():
    """
    Create a fresh NullPool async session for Celery forked workers.
    NullPool avoids the 'Future attached to a different loop' error that occurs
    when the module-level pooled engine from database.py is reused across asyncio.run() calls.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool
    worker_engine = create_async_engine(
        settings.database_url,
        echo=False,
        poolclass=NullPool,
    )
    return async_sessionmaker(worker_engine, class_=AsyncSession, expire_on_commit=False)


@app.task(bind=True, max_retries=3, default_retry_delay=30)
def process_document(self, document_id: str, file_path: str) -> dict:
    """Full ingestion pipeline for a single document. Runs synchronously via asyncio.run."""
    try:
        return asyncio.run(_process_document_async(document_id, file_path))
    except Exception as exc:
        log.exception(f"Ingestion failed for {document_id}: {exc}")
        raise self.retry(exc=exc)


async def _process_document_async(document_id: str, file_path: str) -> dict:
    AsyncSessionLocal = _make_worker_session()
    from access_control.models import ClassificationEnum, Document
    from access_control.rbac import acl_payload_for_chunk
    from ingestion.chunker import add_contextual_text, chunk_document
    from ingestion.decision_classifier import classify_chunks
    from ingestion.entity_resolver import deduplicate_within_batch
    from ingestion.extractor import extract
    from ingestion.extractor_graph import extract_from_chunks
    from retrieval.graph_store import upsert_entities_and_relations, upsert_decision
    from retrieval.vector_store import upsert_chunks

    path = Path(file_path)
    doc_id = UUID(document_id)

    async with AsyncSessionLocal() as db:
        doc = await db.get(Document, doc_id)
        if doc is None:
            return {"error": "document not found"}

        # Hash check
        current_hash = _file_hash(path)
        if doc.file_hash == current_hash and doc.status == "done":
            return {"skipped": True, "reason": "unchanged"}

        doc.status = "indexing"
        doc.file_hash = current_hash
        await db.commit()

        try:
            # 1. Extract text
            raw_text = extract(file_path, mime_type=doc.mime_type)
            if not raw_text.strip():
                doc.status = "error"
                doc.error_message = "No text extracted"
                await db.commit()
                return {"error": "no text"}

            # 2. Hierarchical chunking
            chunks = chunk_document(raw_text)

            # 3. Contextual retrieval (async, uses LLM with prompt caching)
            chunks = await add_contextual_text(chunks, raw_text)

            # 4. ACL classification heuristic
            classification = _classify_document(doc.title, raw_text)
            doc.classification = classification

            # 5. Build ACL payload for Qdrant
            acl_payload = acl_payload_for_chunk(
                classification=classification,
                allowed_roles=doc.allowed_roles,
                allowed_departments=doc.allowed_departments,
                allowed_users=doc.allowed_users,
            )

            # 6. Embed + upsert into Qdrant (child chunks only)
            child_chunks = [c for c in chunks if not c.is_parent]
            await upsert_chunks(
                document_id=document_id,
                document_title=doc.title,
                chunks=child_chunks,
                base_payload={**acl_payload, "document_title": doc.title, "source_type": doc.source_type},
            )

            # 7. Persist chunks to Postgres
            from access_control.models import Chunk
            from sqlalchemy import delete
            await db.execute(delete(Chunk).where(Chunk.document_id == doc_id))
            for c in chunks:
                db.add(Chunk(
                    id=c.id,
                    document_id=doc_id,
                    parent_chunk_id=c.parent_id,
                    original_text=c.original_text,
                    contextualized_text=c.contextualized_text,
                    embedding_model=settings.embedding_model,
                    chunk_index=c.chunk_index,
                    char_start=c.char_start,
                    char_end=c.char_end,
                    is_parent=c.is_parent,
                    acl_version=doc.acl_version,
                ))
            await db.commit()

            # 8. Entity extraction (uses contextualized text for better extraction)
            texts_for_extraction = [
                c.contextualized_text or c.original_text for c in child_chunks
            ]
            extraction = await extract_from_chunks(texts_for_extraction)
            deduped_entities = deduplicate_within_batch(extraction.entities)

            # 9. Graph upsert (Apache AGE via Postgres)
            # Pass db so graph_store reuses the same NullPool connection (no loop mismatch).
            entity_name_to_id = await upsert_entities_and_relations(
                entities=deduped_entities,
                relations=extraction.relations,
                source_document_id=document_id,
                acl_roles=doc.allowed_roles,
                classification=classification.value,
                db=db,
            )

            # 10. Decision Trail detection
            chunk_id_texts = [
                (str(c.id), c.contextualized_text or c.original_text)
                for c in child_chunks
            ]
            detected_decisions = await classify_chunks(chunk_id_texts)
            for decision in detected_decisions:
                await upsert_decision(
                    decision=decision,
                    source_document_id=document_id,
                    acl_roles=doc.allowed_roles,
                    classification=classification.value,
                    db=db,
                )

            doc.status = "done"
            doc.chunk_count = len(child_chunks)
            await db.commit()

            return {
                "document_id": document_id,
                "chunks": len(child_chunks),
                "entities": len(deduped_entities),
                "decisions": len(detected_decisions),
            }

        except Exception as exc:
            doc.status = "error"
            doc.error_message = str(exc)[:500]
            await db.commit()
            raise


def _classify_document(title: str, text: str) -> "ClassificationEnum":
    from access_control.models import ClassificationEnum

    combined = (title + " " + text[:2000]).lower()
    for keyword in settings.confidential_keyword_list:
        if keyword in combined:
            return ClassificationEnum.confidential
    return ClassificationEnum.internal
