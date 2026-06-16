# Company Brain — Developer Guide

## Starting the stack

```bash
cp .env.example .env
# Edit .env: set POSTGRES_PASSWORD, ANTHROPIC_API_KEY (or your chosen LLM provider)

docker compose up --build
# First run prints the default admin password to stdout.
```

Services:
- **Backend API**: http://localhost:8000 — `GET /health` to verify
- **Frontend**: http://localhost:3000
- **Qdrant UI**: http://localhost:6333/dashboard
- **Postgres**: localhost:5432 (user=brain, db=company_brain)

Optional fully-local LLM (Ollama):
```bash
docker compose --profile local-llm up
```

## Running backend locally (outside Docker)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Requires Postgres (with AGE extension), Qdrant, Redis running locally
export DATABASE_URL="postgresql+asyncpg://brain:changeme@localhost:5432/company_brain"
export QDRANT_URL="http://localhost:6333"
export REDIS_URL="redis://localhost:6379/0"
export ANTHROPIC_API_KEY="sk-ant-..."

alembic upgrade head
uvicorn main:app --reload --port 8000
```

Celery worker (separate terminal):
```bash
celery -A ingestion.worker worker --loglevel=info
```

## Running frontend locally

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173 (proxied to backend at :8000)
```

## Architecture

```
Query flow:
  POST /api/query/
    → access_control/rbac.py: ACLContext from JWT
    → retrieval/query_router.py: classify (vector | graph | hybrid | decision)
    → retrieval/vector_store.py: Qdrant search with ACL pre-filter (RRF fusion)
    → retrieval/reranker.py: cross-encoder re-score
    → retrieval/graph_store.py: AGE Cypher traversal (if mode != vector)
    → access_control/rbac.py: Postgres post-filter (defense-in-depth)
    → retrieval/context_fusion.py: build LLM context string
    → llm/adapter.py: call configured LLM provider
    → access_control/audit.py: write access_audit record

Ingestion flow (Celery task):
  ingestion/worker.py: process_document(document_id, file_path)
    → ingestion/extractor.py: extract text (PyMuPDF, PaddleOCR, python-docx, etc.)
    → ingestion/chunker.py: hierarchical chunk + contextual retrieval (AGE cached prefix)
    → access_control/rbac.py: classify ACL + build Qdrant payload
    → retrieval/vector_store.py: embed (BGE-large local) + upsert Qdrant
    → ingestion/extractor_graph.py: entity/relation extraction (Haiku)
    → ingestion/entity_resolver.py: deduplicate entity names
    → retrieval/graph_store.py: AGE graph upsert via Cypher
    → ingestion/decision_classifier.py: detect decisions (confidence ≥ 0.75)
    → retrieval/graph_store.py: create Decision nodes in AGE
```

## Key invariants

**Qdrant collection**: `company_brain_chunks` — dense (BGE-large, 1024-dim) + sparse (BM25). Do not change the collection name without deleting the existing collection and re-indexing.

**Apache AGE graph**: `company_brain` — lives inside Postgres. Connect via psycopg2/asyncpg. Run `LOAD 'age'; SET search_path = ag_catalog, '$user', public;` before any AGE query.

**`original_text` vs `contextualized_text`**: `original_text` is always shown to users in citations. `contextualized_text` (= context + "\n\n" + original) is used ONLY for embedding and BM25 indexing. Never expose `contextualized_text` to users.

**RBAC defense-in-depth**: Qdrant pre-filter uses denormalized boolean fields (`allowed_role_<role>: true`). Postgres post-filter re-checks `document_acl` table. Both must pass. The Postgres check catches stale Qdrant payloads after ACL version bumps.

**ACL version bumps**: When document permissions change, `doc.acl_version` is incremented and `retrieval/vector_store.py::update_acl_payload()` is called to update Qdrant payloads. No re-embedding required — metadata only.

**LLM providers**: Configured via `LLM_PROVIDER` env var (claude | openai | azure | ollama). Extraction/routing uses `EXTRACTION_LLM_PROVIDER` (default: claude/haiku). Context generation uses `CONTEXT_LLM_PROVIDER` (default: claude/haiku with prompt caching).

## Database migrations

```bash
# Create a new migration (after changing models.py)
alembic revision --autogenerate -m "describe the change"

# Apply
alembic upgrade head

# Rollback one step
alembic downgrade -1
```

## Verification checklist (Phase 1)

1. `docker compose up` → all services healthy; admin password printed in logs
2. Login as admin at http://localhost:3000
3. Upload test docs (PDF, DOCX, XLSX) → confirm status becomes "done" and chunk_count > 0
4. Ask a simple fact question → verify answer cites the correct document
5. Create Employee user (dept=Engineering) → query a confidential doc → confirm empty answer + `access_audit` denial logged
6. **Adversarial RBAC**: revoke doc access → query immediately → confirm 0 results
7. Ask multi-hop relational question → confirm `retrieval_mode: hybrid` in response
8. Verify AGE graph: `SELECT * FROM cypher('company_brain', $$ MATCH (n) RETURN n LIMIT 10 $$) AS (n agtype);`

## Phase 1.5 (MCP Server + Agentic Execution + Knowledge Health)

Planned modules:
- `backend/mcp_server/` — POST /mcp JSON-RPC 2.0 endpoint
- `backend/agent/executor.py` — post-answer action proposals
- `backend/ingestion/quality_monitor.py` — Celery beat scheduled health check

Do not implement until Phase 1 RBAC adversarial tests all pass.
