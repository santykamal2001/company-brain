# Company Brain — AI-Native Institutional Memory Platform

> *"Institutional memory becomes valuable when it is current, connected, updated and executable."*

Company Brain is a **self-hosted, AI-native knowledge platform** that acts like an informed employee who knows everything the company knows — but only tells each person what they are authorized to know. It ingests all company knowledge (files, wikis, Slack, email, calendar), builds a living knowledge graph, and answers natural-language questions with strict role-based access control enforced at the chunk and graph-node level — not just at the API.

---

## Table of Contents

- [Why Company Brain](#why-company-brain)
- [The Three-Layer Product](#the-three-layer-product)
- [Key Differentiators](#key-differentiators)
- [Competitor Comparison](#competitor-comparison)
- [Architecture Overview](#architecture-overview)
- [Query Flow (Step by Step)](#query-flow-step-by-step)
- [Ingestion Pipeline (Step by Step)](#ingestion-pipeline-step-by-step)
- [Tech Stack](#tech-stack)
- [Knowledge Graph Schema](#knowledge-graph-schema)
- [RBAC & Permission Model](#rbac--permission-model)
- [Contextual Retrieval](#contextual-retrieval)
- [Decision Trail](#decision-trail)
- [Getting Started](#getting-started)
- [Configuration Reference](#configuration-reference)
- [API Reference](#api-reference)
- [Frontend Pages](#frontend-pages)
- [Project Structure](#project-structure)
- [Roadmap](#roadmap)

---

## Why Company Brain

Every company loses institutional knowledge every day. When an employee leaves, their context goes with them. When a decision is made in a Slack thread, it evaporates. When a new hire joins, they spend months figuring out "why do we do it this way?" by asking around.

Existing tools fail in predictable ways:

- **Search tools** (Glean, Guru) find documents but can't reason across them or answer relational questions.
- **Wiki tools** (Confluence, Notion) require humans to keep them updated — they're always stale.
- **Generic AI assistants** (ChatGPT, Copilot) have no access to your company's private knowledge and hallucinate freely.
- **Cloud RAG tools** require sending your data to a third party — a hard blocker for regulated industries.

**Company Brain solves all four**: it ingests everything automatically, reasons across connected knowledge via a graph, answers in natural language, and runs entirely on your own infrastructure with zero data leaving your network.

---

## The Three-Layer Product

```
┌─────────────────────────────────────────────────────────────────┐
│  KNOW  — Hybrid Graph RAG + Contextual Retrieval                │
│  Answer any question by combining vector similarity search      │
│  with graph traversal, routed per question type.                │
├─────────────────────────────────────────────────────────────────┤
│  REMEMBER  — Decision Trail + Knowledge Health Score            │
│  Capture the "why" behind every organizational decision.        │
│  Monitor knowledge freshness, conflicts, and coverage gaps.     │
├─────────────────────────────────────────────────────────────────┤
│  ACT  — MCP Server + Agentic Execution                          │
│  Expose governed retrieval to every AI agent in the enterprise. │
│  Take actions (Jira, Slack, Calendar) with on-prem RBAC.        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Differentiators

### 1. Hybrid Graph RAG
Most RAG systems only do vector similarity search — they find chunks that *look like* the question. Company Brain runs two retrieval engines in parallel:

- **Vector search** (Qdrant, BGE-large embeddings, BM25 hybrid): fast semantic similarity, best for "what is X?" questions.
- **Knowledge graph traversal** (Apache AGE / Postgres, Cypher): walks typed relationships to answer "who works on X?", "what does team Y depend on?", "which projects involve both Alice and Bob?" questions that vector search can't handle.

A query router classifies each question and directs it to the right engine — or both.

### 2. Contextual Retrieval
Before embedding a chunk, Company Brain prepends 50–100 words of LLM-generated context situating that chunk within its source document. This means a chunk like *"the deadline was pushed to Friday"* becomes *"In a Slack thread about the Q3 product launch, the team discussed timeline changes. The deadline was pushed to Friday."* — dramatically improving retrieval quality for context-free messages (Slack, email, meeting notes).

- Reduces retrieval failure by **49%** (vector) or **67%** (vector + BM25 hybrid) per Anthropic's 2025 research.
- Uses Anthropic prompt caching — the document body is cached across all its chunks, reducing cost by ~80%.
- `contextualized_text` is used only for embedding and BM25 indexing. Users always see the original text in citations.

### 3. Decision Trail
No other tool captures *decisions* as first-class knowledge objects. When Company Brain indexes a Slack thread, email chain, or meeting note, a classifier detects whether a decision was made. If so, it creates a structured `Decision` node in the knowledge graph:

- **What** was decided (1–2 sentence summary)
- **Who** made the decision (linked to `Person` nodes)
- **When** (timestamp)
- **What alternatives** were considered
- **What prior decision** this supersedes
- **Evidence chunks** (which source texts contain the proof)

This directly answers the questions employees can't answer today: *"Why do we use Postgres?"*, *"Who approved the reorg?"*, *"What did leadership consider before choosing vendor X?"*

### 4. Chunk-Level + Graph-Node-Level RBAC
Competitors (Glean, Onyx) enforce permissions at the document level — if you can access the document, you get all of it. Company Brain enforces at the **chunk level**: the LLM literally never sees a chunk the user isn't authorized to read. Graph nodes inherit the most-restrictive ACL from their source chunks, so even graph traversal cannot leak confidential entity information to unauthorized users.

### 5. Self-Hosted, Data Never Leaves Your Network
Single-command Docker deployment. Enterprise customers own their data, their compute, and their LLM choice. No SaaS dependency required. Critical for regulated industries (finance, legal, healthcare, government).

### 6. MCP Server (Phase 1.5)
Company Brain exposes itself as an MCP-compliant server (the [Model Context Protocol](https://modelcontextprotocol.io) standard adopted by Anthropic, OpenAI, Google, and the Linux Foundation in December 2025). Any MCP-compatible AI agent — Claude Code, GitHub Copilot, Cursor, internal tools — can query Company Brain for governed company knowledge. This transforms the product from an app employees open into **infrastructure every AI tool in the enterprise depends on**.

### 7. Per-Answer Provenance (EU AI Act Article 13)
Every query writes an immutable `access_audit` record: which user asked, which chunks were returned, which were denied, which ACL version was in effect, and when. This satisfies EU AI Act Article 13 traceability obligations (enforcement deadline: August 2, 2026) that SaaS competitors cannot cleanly produce.

---

## Competitor Comparison

| Capability | Glean | Onyx | **Company Brain** |
|---|---|---|---|
| Self-hosted / on-premise | No (SaaS, $40K+/yr) | Yes (open source) | **Yes** |
| Knowledge graph | Yes (SaaS-hosted) | Yes (document-level) | **Yes (chunk+node level, self-hosted)** |
| Contextual retrieval | Unconfirmed | Yes | **Yes** |
| Hybrid BM25 + vector | Partial | Yes | **Yes** |
| **Decision Trail** | **No** | **No** | **Yes — unique** |
| **Per-answer provenance (Article 13)** | **No** | **No** | **Yes — unique** |
| RBAC enforced at chunk/node level | Partial (doc-level) | Partial (doc-level) | **Yes (chunk + graph node)** |
| MCP server (queryable knowledge substrate) | No | Limited | **Yes (Phase 1.5)** |
| Agentic execution | Yes (cloud-only) | Yes (via MCP) | **Yes (on-prem, RBAC-enforced)** |
| Compliance audit log export | No | No | **Yes** |
| Free / self-hosted | No | Yes | **Yes** |

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              COMPANY BRAIN                                    │
│                                                                                │
│  ┌─────────────┐    ┌──────────────────────────────────────────────────────┐  │
│  │   FRONTEND  │    │                    BACKEND (FastAPI)                  │  │
│  │  React/Vite │◄───┤                                                      │  │
│  │  Port 3000  │    │  ┌──────────┐  ┌──────────────┐  ┌───────────────┐  │  │
│  └─────────────┘    │  │  Auth /  │  │   Query API  │  │  Document API │  │  │
│                     │  │  Users   │  │  /api/query  │  │  /api/docs    │  │  │
│  ┌─────────────┐    │  └──────────┘  └──────┬───────┘  └───────┬───────┘  │  │
│  │   EXTERNAL  │    │                        │                  │           │  │
│  │   CLIENTS   │    │            ┌───────────▼──────────┐       │           │  │
│  │  MCP Agents │───►│            │     agent/brain.py   │       │           │  │
│  │  (Phase 1.5)│    │            │  (orchestrates full  │       │           │  │
│  └─────────────┘    │            │   retrieval pipeline)│       │           │  │
│                     │            └───────────┬──────────┘       │           │  │
│                     │                        │                  │           │  │
│                     │  ┌─────────────────────▼──────────────────▼────────┐ │  │
│                     │  │               RETRIEVAL LAYER                    │ │  │
│                     │  │                                                  │ │  │
│                     │  │  query_router.py → vector | graph | hybrid |     │ │  │
│                     │  │                    decision                      │ │  │
│                     │  │                                                  │ │  │
│                     │  │  vector_store.py    graph_store.py               │ │  │
│                     │  │  (Qdrant RRF)       (Apache AGE/Postgres)        │ │  │
│                     │  │       │                    │                     │ │  │
│                     │  │  reranker.py        graph_retrieval.py           │ │  │
│                     │  │  (cross-encoder)    (Cypher traversal)           │ │  │
│                     │  │       │                    │                     │ │  │
│                     │  │  rbac.py post-filter (Postgres source-of-truth)  │ │  │
│                     │  │       │                    │                     │ │  │
│                     │  │  context_fusion.py (merge chunks + graph triples)│ │  │
│                     │  └──────────────────────┬─────────────────────────-┘ │  │
│                     │                         │                             │  │
│                     │            ┌────────────▼────────────┐               │  │
│                     │            │      llm/adapter.py      │               │  │
│                     │            │  Claude | OpenAI | Azure │               │  │
│                     │            │  Ollama (fully local)    │               │  │
│                     │            └─────────────────────────┘               │  │
│                     │                                                       │  │
│                     │  ┌──────────────────────────────────────────────────┐ │  │
│                     │  │              INGESTION LAYER (Celery)             │ │  │
│                     │  │                                                   │ │  │
│                     │  │  extractor.py → chunker.py → extractor_graph.py  │ │  │
│                     │  │  entity_resolver.py → decision_classifier.py     │ │  │
│                     │  └──────────────────────────────────────────────────┘ │  │
│                     └──────────────────────────────────────────────────────┘  │
│                                                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Postgres   │  │    Qdrant    │  │    Redis     │  │     Ollama       │  │
│  │  + AGE ext.  │  │  (vectors)   │  │  (job queue) │  │  (optional LLM)  │  │
│  │  (graph +    │  │  Port 6333   │  │  Port 6379   │  │  --profile       │  │
│  │   metadata)  │  │              │  │              │  │  local-llm       │  │
│  │  Port 5432   │  │              │  │              │  │                  │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Query Flow (Step by Step)

When a user asks a question, the following sequence executes:

```
User question: "Which people are involved in both the payments project and the fraud team?"

Step 1 — RBAC Context
  api/auth.py: decode JWT → extract user_id, role, department
  rbac.py: build ACLContext { role: Employee, dept: Engineering, project_ids: [...] }

Step 2 — Query Classification
  query_router.py:
    ├── Heuristic regex scan: "both X and Y" → HYBRID mode (no LLM call needed)
    └── Entity extraction: ["payments project", "fraud team"]

Step 3 — Vector Search (Qdrant)
  vector_store.py:
    ├── Embed question with BGE-large-en-v1.5 (local, $0 cost)
    ├── Pre-filter: allowed_role_employee=true AND (no_dept_restriction OR allowed_dept_engineering=true)
    ├── Dense vector search (cosine similarity)
    ├── Sparse vector search (BM25)
    ├── RRF fusion: score[id] += 1 / (60 + rank)
    └── Return top 32 candidates

Step 4 — Cross-Encoder Reranking
  reranker.py:
    └── cross-encoder/ms-marco-MiniLM-L-6-v2 re-scores all 32 candidates → top 16

Step 5 — Graph Traversal (Apache AGE / Postgres)
  graph_store.py:
    ├── Anchor on "payments project" → find Project node
    ├── Anchor on "fraud team" → find Team node
    ├── Depth-1 Cypher traversal:
    │     MATCH (p:Person)-[:WORKS_ON]->(proj:Project {name: 'Payments'})
    │     WHERE proj.acl_roles CONTAINS 'Employee'
    │     RETURN p, proj
    ├── Filter: Person nodes with ACL ⊇ Employee
    └── Convert to triples: "Alice Kim WORKS_ON Payments Project (role: Lead)"

Step 6 — RBAC Post-Filter (Defense-in-Depth)
  rbac.py: post_filter_chunks(candidate_ids, acl, db)
    ├── Re-checks document_acl table in Postgres (source of truth)
    ├── Catches any stale Qdrant payloads after ACL version bumps
    └── Returns (allowed_ids, denied_ids) — denied count returned to UI

Step 7 — Context Fusion
  context_fusion.py:
    ├── =ORGANIZATIONAL CONTEXT (from knowledge graph)=
    │     Alice Kim WORKS_ON Payments Project (role: Lead)
    │     Bob Lee PART_OF Fraud Team
    │     ...
    └── =RELEVANT DOCUMENT EXCERPTS=
          [Chunk 1] team_structure.xlsx — "Alice Kim leads the payments integration..."
          [Chunk 2] org_chart.pdf — "Fraud team consists of..."

Step 8 — LLM Generation
  llm/adapter.py → configured provider (Claude / OpenAI / Azure / Ollama)
    └── Answer with citations, grounded in retrieved context

Step 9 — Audit Logging
  audit.py: write access_audit record (fire-and-forget)
    └── { user_id, query_hash, returned_chunk_ids, denied_chunk_ids, acl_version, timestamp, caller_type }

Response: { answer, sources, retrieval_mode: "hybrid", graph_entities_used, denied_chunk_count, latency_ms }
```

---

## Ingestion Pipeline (Step by Step)

When a file is uploaded, a Celery background task runs the full 11-step pipeline:

```
File uploaded: strategy_deck.pdf (2.4 MB)

Step 1 — Hash Check
  MD5(first 1MB + last 1MB) → compare with stored hash
  └── If unchanged: skip (no re-processing, no re-embedding)

Step 2 — Text Extraction
  extractor.py:
    ├── PDF → PyMuPDF (text-layer extraction)
    ├── Scanned PDF → PaddleOCR fallback
    ├── DOCX → python-docx
    ├── XLSX → openpyxl
    └── PPTX → python-pptx

Step 3 — Hierarchical Chunking
  chunker.py:
    ├── Parent chunks: ~3500 chars (section-level, break at natural boundaries)
    └── Child chunks: 512 chars / 50 char overlap (precision retrieval)
        Every child records parent_chunk_id for context expansion

Step 4 — Contextual Retrieval Generation
  chunker.py (if CONTEXTUAL_RETRIEVAL_ENABLED=true):
    ├── For EACH child chunk, call the context LLM (Haiku) with:
    │     <document>{full document text}</document>  ← cached as ephemeral prefix
    │     <chunk>{chunk text}</chunk>
    │     Situate this chunk in 50-100 words for retrieval.
    ├── contextualized_text = context_output + "\n\n" + original_text
    ├── Anthropic prompt caching: document body cached across all chunk calls
    │   → ~80% cost reduction vs. naive repeated calls
    └── Store both original_text and contextualized_text in Postgres
        (original_text shown to users; contextualized_text used for embedding/BM25)

Step 5 — ACL Classification
  worker.py:
    ├── Heuristic: filename/section keywords → "salary", "attorney" → confidential
    ├── Default: internal
    └── ACL payload built: { classification, allowed_roles, allowed_departments,
                              allowed_role_admin: true, allowed_role_employee: true,
                              no_dept_restriction: true, acl_version: 1 }

Step 6 — Embedding + Qdrant Upsert
  vector_store.py:
    ├── Embed contextualized_text with BGE-large-en-v1.5 (local, 1024-dim, $0 cost)
    ├── BM25 sparse vectors indexed in Qdrant natively
    ├── Upsert into "company_brain_chunks" collection
    │   Payload includes full ACL metadata + entity_ids (back-filled in Step 10)
    └── Create payload indexes on allowed_role_* and no_dept_restriction

Step 7 — Entity & Relation Extraction
  extractor_graph.py:
    ├── Batch 3-5 child chunks per LLM call (Claude Haiku via forced tool-use)
    ├── Feed contextualized_text (not original) for richer entity context
    └── Output:
        {
          "entities": [
            {"name": "Alice Kim", "type": "Person", "description": "VP of Product"},
            {"name": "Q3 Growth", "type": "Project", "description": "Revenue expansion initiative"}
          ],
          "relations": [
            {"source": "Alice Kim", "target": "Q3 Growth", "rel_type": "WORKS_ON", "description": "Leads the project"}
          ]
        }

Step 8 — Entity Resolution
  entity_resolver.py:
    ├── Normalize: "Alice Kim", "A. Kim", "alice kim" → canonical form
    ├── AGE graph lookup: does a node with this name already exist?
    ├── Fuzzy merge: LLM-assisted for ambiguous near-matches (threshold: 0.85)
    └── Log merges to resolution_log

Step 9 — AGE Graph Upsert (Apache AGE / Postgres)
  graph_store.py:
    ├── MERGE (upsert) entity nodes via Cypher over asyncpg
    ├── Create typed edges between entities
    ├── Link every entity to source chunk: (entity)-[:MENTIONED_IN]->(chunk)
    └── Propagate ACL: most-restrictive-wins if entity appears in chunks
        of different classifications

Step 10 — Back-Link Entity IDs to Qdrant
  vector_store.py: update_payload(chunk_id, {entity_ids: [...]})
    └── Metadata-only update — no re-embedding required

Step 11 — Decision Classification
  decision_classifier.py:
    ├── Batch LLM call over newly ingested chunks:
    │     "Does this chunk record a decision? If yes: what, who, when, alternatives?"
    ├── On confidence ≥ 0.75: create Decision node in AGE graph
    │     Decision { title, summary, decided_at, alternatives_considered[], evidence_chunk_ids[] }
    ├── Link: (Decision)-[:MADE_BY]->(Person[])
    ├── Link: (Decision)-[:ABOUT]->(Topic|Project)
    └── Propagate ACL from source chunks

  document.status → "done", chunk_count → N
```

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Backend API | FastAPI (Python) | Async-first, fast, excellent type support |
| Frontend | React + TypeScript + Vite | Fast dev server, type-safe, modern |
| Primary DB | PostgreSQL 16 | Production-grade, ACID, same container as graph |
| Knowledge Graph | Apache AGE (Postgres extension) | Cypher-compatible, runs inside Postgres — no extra container, backup, or connection pool |
| Vector Store | Qdrant (self-hosted) | Best metadata filtering, hybrid dense+sparse, production-ready |
| Embeddings | BAAI/bge-large-en-v1.5 | 1024-dim, state-of-art quality, $0 cost, runs locally |
| Reranker | cross-encoder/ms-marco-MiniLM-L-6-v2 | Fast local cross-encoder, no API calls |
| Job Queue | Celery + Redis | Reliable background ingestion, retries, concurrency control |
| LLM (default) | Claude (Anthropic) | Best contextual retrieval quality, prompt caching support |
| LLM (local) | Ollama | Fully offline option for air-gapped environments |
| Auth | JWT (access 15m + refresh 7d) + SSO | httpOnly cookies, SAML 2.0 / OIDC via python-saml + authlib |
| ORM / Migrations | SQLAlchemy (async) + Alembic | Type-safe, async sessions, schema versioning |
| Containerization | Docker Compose | Single `docker compose up` to start everything |

---

## Knowledge Graph Schema

The graph lives inside Postgres via the Apache AGE extension (`company_brain` graph). All nodes and edges use the openCypher query language.

### Node Types

```
Person(id, canonical_name, email_hint, department, title, aliases[], acl_roles[])
Team(id, name, department, aliases[])
Project(id, name, status, owner_id, acl_roles[])
Topic(id, name, category, description)
  └── e.g. "Product Roadmap", "Hiring", "Q3 Revenue"
Process(id, name, type)
  └── e.g. "Onboarding", "Code Review", "Budget Approval"
Asset(id, name, asset_type, location)
Event(id, title, date, participants[])
  └── meetings, launches, incidents
Document(id, source_id, title, source_type, url, created_date, acl_roles[])

Decision(id, title, summary, decided_at, confidence FLOAT,
         alternatives_considered TEXT[], supersedes_decision_id,
         evidence_chunk_ids[], acl_roles[])
  └── THE most differentiated node type. Captures institutional reasoning.
      "Why do we use Postgres?" → Decision node.
      "Who approved the reorg?" → Decision node + MADE_BY edges.
```

### Edge Types

```
WORKS_ON(Person → Project, role STRING)
PART_OF(Person → Team)
OWNS(Person → Project | Process)
AUTHORED(Person → Document)
DISCUSSED_IN(Topic → Document | Event)
TAGGED_WITH(Document → Topic)
DEPENDS_ON(Project → Project)
INVOLVES(Event → Person | Project)
MENTIONED_IN(* → Document, chunk_id STRING)   ← provenance for all entities

MADE_BY(Decision → Person[])                  ← who were the decision makers
RESULTED_IN(Event → Decision)                 ← which meeting produced this decision
ABOUT(Decision → Topic | Project)             ← what domain this decision governs
SUPERSEDES(Decision → Decision)               ← decision history chain
```

### Verify Graph Contents

```sql
-- Connect to Postgres and run:
LOAD 'age';
SET search_path = ag_catalog, '$user', public;

SELECT * FROM cypher('company_brain', $$
  MATCH (n) RETURN labels(n), n.canonical_name LIMIT 20
$$) AS (label agtype, name agtype);

-- Find all decisions:
SELECT * FROM cypher('company_brain', $$
  MATCH (d:Decision)-[:MADE_BY]->(p:Person)
  RETURN d.title, d.summary, p.canonical_name
$$) AS (title agtype, summary agtype, made_by agtype);
```

---

## RBAC & Permission Model

### Role Hierarchy

| Role | Access Level |
|---|---|
| `Admin` | All departments, all classifications, all documents |
| `Manager` | Full access within assigned departments/projects |
| `Employee` | Internal-level access within their department and assigned projects |
| `Guest` | Read-only, `classification=public` or explicitly shared docs only |

### Document Classification

Every document and chunk carries an ACL:

```
classification:       public | internal | confidential | restricted
allowed_roles:        [Admin, Manager, Employee, ...]
allowed_departments:  [engineering, hr, finance, ...]   # empty = all departments
allowed_users:        [user_id, ...]                    # explicit whitelist
acl_version:          int                               # bumped on permission change
```

### Two-Layer Defense-in-Depth

```
Layer 1 — Qdrant Pre-Filter (hot path, no Postgres join)
  Denormalized boolean fields on every chunk payload:
    allowed_role_admin: true | false
    allowed_role_manager: true | false
    allowed_role_employee: true | false
    allowed_role_guest: true | false
    allowed_dept_engineering: true | false
    no_dept_restriction: true | false

  Qdrant filter at query time:
    must: [{ key: "allowed_role_employee", match: { value: true } }]
    should: [{ key: "no_dept_restriction", ... }, { key: "allowed_dept_engineering", ... }]

Layer 2 — Postgres Post-Filter (defense-in-depth, catches stale Qdrant payloads)
  Re-checks document_acl table before any chunk enters LLM context.
  Catches ACL changes that haven't propagated to Qdrant yet.
  Returns (allowed_ids, denied_ids) — denial count surfaced in API response.
```

### Graph-Level ACL

Every entity node inherits the **most restrictive** ACL from its source chunks. If "Alice Kim" is mentioned in a public chunk (engineering org chart) AND a confidential chunk (salary data), her node carries `classification=confidential`. A guest user's graph traversal never returns triples sourced from confidential chunks.

### ACL Version Bumps (No Re-Embedding)

When document permissions change:
```
PATCH /api/documents/{id}/acl
  → bump doc.acl_version
  → call vector_store.update_acl_payload(chunk_ids, new_payload)
  → Qdrant payload update only (metadata, no re-embedding)
```

### Adversarial RBAC Tests (Phase 1 Pass/Fail Gates)

| Test | What It Verifies |
|---|---|
| **Stale metadata test** | Revoke access → update Qdrant → query immediately → 0 results |
| **Graph node bleed test** | Entity in public + confidential chunks → guest gets no confidential triples |
| **Cross-dept boundary test** | Engineering employee queries HR restricted doc → 0 results from Qdrant pre-filter |
| **MCP token scope test** | Guest-scoped MCP token → confidential chunks never returned |

---

## Contextual Retrieval

Standard RAG embeds raw text chunks. The problem: chunks from Slack, email, and meeting notes are full of context-free text.

```
Raw chunk (bad for retrieval):
  "The deadline was pushed to Friday."

Contextualized chunk (good for retrieval):
  "In a Slack thread about the Q3 mobile app launch, the engineering team
   discussed timeline adjustments after a dependency delay. The deadline
   was pushed to Friday."
```

### How It Works

For each document, Company Brain calls a cheap LLM (Haiku by default) once per chunk with the full document body as an **Anthropic prompt-cached prefix**:

```
System: Generate context for retrieval.

[CACHED] <document>
{full document text — cached across all chunk calls from this file}
</document>

[NOT CACHED] <chunk>
{chunk text}
</chunk>

Give a short context (50-100 words) situating this chunk within the document.
```

The document body is marked `cache_control: {type: "ephemeral"}` — Anthropic caches it on their servers across all chunk calls for the same file, reducing cost by ~80%.

### Storage

```sql
chunks table:
  original_text       TEXT   -- shown to users in citations (never contextualized text)
  contextualized_text TEXT   -- used for embedding + BM25 indexing only
```

**The rule is absolute**: users always see `original_text`. `contextualized_text` is internal retrieval infrastructure.

---

## Decision Trail

The Decision Trail is the feature that answers questions no other tool can: *Why did we choose this? Who decided that? What did we consider?*

### Detection

After ingestion, `decision_classifier.py` runs a batched LLM scan over new chunks:

```
Prompt: Analyze these chunks. For each, determine:
1. Does this record a decision, conclusion, or resolution? (yes/no + confidence 0-1)
2. If yes: what was decided, who decided it, when, what alternatives were considered,
   what prior decision does this supersede?
Output structured JSON.
```

Decisions detected with `confidence ≥ 0.75` create a `Decision` node in the AGE graph.

### Query Routing

Questions containing these patterns route to Decision Trail mode before vector search:

- "why do we", "why did we", "why are we"
- "who decided", "who approved", "who chose"
- "rationale", "reason we", "reason for"
- "history of", "background on", "what led to"

### Example

```
User: "Why do we use Postgres instead of MySQL?"

Decision Trail mode:
  → Find Decision nodes tagged ABOUT("Database Technology")
  → Decision: { title: "Database selection 2023",
                summary: "Team chose Postgres for its JSONB support and AGE graph extension",
                decided_at: "2023-03-15",
                made_by: ["Alice Kim", "Bob Lee"],
                alternatives_considered: ["MySQL", "MongoDB", "CockroachDB"],
                supersedes: null,
                evidence_chunk_ids: ["abc123", "def456"] }
  → Return answer with decision context + source citations
```

---

## Getting Started

### Prerequisites

- Docker and Docker Compose
- An LLM API key (Anthropic, OpenAI, or Azure) — or use Ollama for fully local

### Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/santykamal2001/company-brain.git
cd company-brain

# 2. Configure environment
cp .env.example .env

# Edit .env — at minimum, set:
#   POSTGRES_PASSWORD=your_strong_password
#   ANTHROPIC_API_KEY=sk-ant-...   (or your chosen provider's key)
#   JWT_SECRET=a_random_32_char_string

# 3. Start all services
docker compose up --build

# The first run will:
#   - Run Postgres migrations (including CREATE EXTENSION age)
#   - Initialize the AGE knowledge graph schema
#   - Create the Qdrant collection (dense + sparse vectors)
#   - Create a default Admin user and print the password to stdout

# 4. Open the app
open http://localhost:3000
# Login with admin@company-brain.local and the printed password
```

### Optional: Fully Local LLM (Ollama)

```bash
# Start with Ollama profile
docker compose --profile local-llm up

# Pull a model inside the Ollama container
docker exec -it company-brain-ollama-1 ollama pull llama3

# Set in .env:
#   LLM_PROVIDER=ollama
#   OLLAMA_BASE_URL=http://ollama:11434
#   LLM_MODEL=llama3
```

### Service URLs

| Service | URL | Notes |
|---|---|---|
| Frontend | http://localhost:3000 | React app |
| Backend API | http://localhost:8000 | FastAPI |
| API Docs | http://localhost:8000/docs | Swagger UI |
| Qdrant Dashboard | http://localhost:6333/dashboard | Vector store UI |
| Postgres | localhost:5432 | user=brain, db=company_brain |

### Running Backend Locally (without Docker)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Requires Postgres (with AGE), Qdrant, and Redis running
export DATABASE_URL="postgresql+asyncpg://brain:changeme@localhost:5432/company_brain"
export QDRANT_URL="http://localhost:6333"
export REDIS_URL="redis://localhost:6379/0"
export ANTHROPIC_API_KEY="sk-ant-..."

alembic upgrade head
uvicorn main:app --reload --port 8000

# Celery worker (separate terminal)
celery -A ingestion.worker worker --loglevel=info
```

---

## Configuration Reference

All configuration is via environment variables (`.env` file). See `.env.example` for the full list.

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_PASSWORD` | *(required)* | Postgres password |
| `LLM_PROVIDER` | `claude` | LLM provider: `claude` / `openai` / `azure` / `ollama` |
| `LLM_MODEL` | `claude-sonnet-4-6` | Model for answer generation |
| `ANTHROPIC_API_KEY` | *(required if claude)* | Anthropic API key |
| `EXTRACTION_LLM_PROVIDER` | `claude` | LLM for entity extraction + routing (can be cheaper) |
| `EXTRACTION_LLM_MODEL` | `claude-haiku-4-5` | Model for extraction/routing |
| `CONTEXTUAL_RETRIEVAL_ENABLED` | `true` | Enable contextual retrieval generation |
| `CONTEXT_LLM_USE_PROMPT_CACHING` | `true` | Use Anthropic prompt caching (~80% cost reduction) |
| `EMBEDDING_MODEL` | `BAAI/bge-large-en-v1.5` | Local embedding model (no API calls) |
| `EMBEDDING_DIM` | `1024` | Embedding dimensions |
| `PARENT_CHUNK_SIZE` | `3500` | Parent chunk size in characters |
| `CHILD_CHUNK_SIZE` | `512` | Child chunk size in characters |
| `CHILD_CHUNK_OVERLAP` | `50` | Overlap between child chunks |
| `GRAPH_ENABLED` | `true` | Enable knowledge graph retrieval |
| `GRAPH_CONTEXT_TOKEN_BUDGET` | `2000` | Max tokens for graph context in LLM prompt |
| `DEFAULT_CLASSIFICATION` | `internal` | Default ACL classification for new documents |
| `CONFIDENTIAL_KEYWORDS` | `salary,...` | Keywords that trigger confidential classification |
| `SSO_ENABLED` | `false` | Enable SAML 2.0 / OIDC SSO |
| `JWT_SECRET` | *(required)* | Secret for JWT signing (min 32 chars) |

---

## API Reference

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/login` | Login with email + password → returns JWT cookies |
| `POST` | `/api/auth/refresh` | Refresh access token using refresh cookie |
| `POST` | `/api/auth/logout` | Clear auth cookies |
| `GET` | `/api/auth/me` | Current user profile |

### Query

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/query/` | Ask a question; returns answer + sources + retrieval metadata |

Request:
```json
{ "question": "Who is working on the payments integration?", "n_results": 8 }
```

Response:
```json
{
  "answer": "Alice Kim (VP of Product) leads the payments integration...",
  "sources": [
    { "document_title": "team_structure.xlsx", "excerpt": "...", "relevance_score": 0.92 }
  ],
  "retrieval_mode": "hybrid",
  "graph_entities_used": ["Alice Kim", "Payments Project"],
  "decision_trail_used": false,
  "chunks_used": 5,
  "denied_chunk_count": 0,
  "latency_ms": 847
}
```

### Documents

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/documents/` | List all documents (scoped to user's ACL) |
| `POST` | `/api/documents/upload` | Upload and index a file |
| `DELETE` | `/api/documents/{id}` | Delete document + chunks + graph nodes |
| `POST` | `/api/documents/{id}/reindex` | Re-process an existing document |
| `PATCH` | `/api/documents/{id}/acl` | Update document permissions (bumps acl_version) |

### Users (Admin only)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/users/` | List all users |
| `POST` | `/api/users/` | Create a user |
| `PATCH` | `/api/users/{id}` | Update role / department / active status |
| `DELETE` | `/api/users/{id}` | Deactivate a user |

### Analytics

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/analytics/queries` | Recent query history with retrieval metadata |
| `GET` | `/api/analytics/denials` | Access denial events |
| `GET` | `/api/analytics/health` | Knowledge health events |

---

## Frontend Pages

| Page | Route | Access | Description |
|---|---|---|---|
| Login | `/login` | Public | Email + password login |
| Chat | `/chat` | All roles | Natural language Q&A with source citations, retrieval mode badge, denied chunk notice |
| Documents | `/documents` | All roles | Upload files, view indexing status, reindex/delete |
| Analytics | `/analytics` | All roles | Query history, denial stats, retrieval score trends |
| Admin | `/admin` | Admin only | User management + knowledge health events |

### Chat UI Features
- **Retrieval mode badge**: `Vector` / `Graph` / `Hybrid` / `Decision` — shows which retrieval engines were used
- **Source citations**: document name, relevance score, text excerpt
- **Decision trail indicator**: highlights when the answer came from a Decision node
- **Denied chunk notice**: "N document sections were filtered by your access permissions" — transparent about what was restricted without revealing what was in them

---

## Project Structure

```
company-brain/
├── backend/
│   ├── main.py                       # FastAPI app + lifespan (migrations, AGE init, Qdrant init)
│   ├── config.py                     # All settings via pydantic-settings
│   ├── database.py                   # SQLAlchemy async engine + AGE schema init
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── api/
│   │   ├── auth.py                   # JWT login/refresh/logout + SSO endpoints
│   │   ├── users.py                  # User CRUD (admin only)
│   │   ├── documents.py              # Upload, index, delete, ACL update
│   │   ├── query.py                  # Main Q&A endpoint
│   │   └── analytics.py             # Query history + health events
│   ├── access_control/
│   │   ├── models.py                 # SQLAlchemy models: User, Document, Chunk, DocumentACL, AccessAudit
│   │   ├── rbac.py                   # ACLContext, Qdrant filter builder, Postgres post-filter
│   │   └── audit.py                 # Per-retrieval audit log writer
│   ├── ingestion/
│   │   ├── worker.py                 # Celery task: full 11-step pipeline
│   │   ├── extractor.py              # Multi-format text extraction
│   │   ├── chunker.py                # Hierarchical chunking + contextual retrieval
│   │   ├── extractor_graph.py        # Entity/relation extraction via LLM tool-use
│   │   ├── entity_resolver.py        # Entity deduplication + merging
│   │   └── decision_classifier.py   # Decision detection → Decision graph nodes
│   ├── retrieval/
│   │   ├── vector_store.py           # Qdrant (upsert, RRF hybrid search, ACL pre-filter)
│   │   ├── graph_store.py            # Apache AGE (schema init, upsert, Cypher traversal)
│   │   ├── query_router.py           # Query classifier: vector | graph | hybrid | decision
│   │   ├── graph_retrieval.py        # Entity-anchored subgraph traversal, token-budgeted
│   │   ├── reranker.py               # Cross-encoder re-scoring
│   │   └── context_fusion.py        # Merge vector chunks + graph triples for LLM prompt
│   ├── agent/
│   │   └── brain.py                  # Orchestrates full query pipeline (ask() function)
│   └── llm/
│       ├── adapter.py                # LLM-agnostic interface (Claude / OpenAI / Azure / Ollama)
│       └── prompts.py               # System prompt + context section templates
├── frontend/
│   ├── src/
│   │   ├── App.tsx                   # Root component, auth state, sidebar nav
│   │   ├── main.tsx                  # React root
│   │   ├── index.css                 # Inter font + base styles
│   │   ├── lib/api.ts                # Typed fetch client for all endpoints
│   │   └── pages/
│   │       ├── Chat.tsx              # Main Q&A interface
│   │       ├── Documents.tsx         # File management
│   │       ├── Admin.tsx             # User management + health events
│   │       ├── Analytics.tsx         # Query history + denial stats
│   │       └── Login.tsx            # Login form
│   ├── index.html
│   ├── vite.config.ts               # Dev server + /api proxy to :8000
│   ├── package.json
│   ├── tsconfig.json
│   ├── nginx.conf                   # Production nginx config (SPA + /api proxy)
│   └── Dockerfile                   # Multi-stage: node build → nginx serve
├── alembic/
│   ├── env.py                       # Async Alembic config
│   └── versions/
│       └── 0001_initial_schema.py   # Full schema + AGE extension + enums
├── docker-compose.yml               # 5 services + optional Ollama profile
├── .env.example                     # All config knobs documented
├── alembic.ini
├── CLAUDE.md                        # Developer guide (invariants, verification checklist)
└── .gitignore
```

---

## Roadmap

### Phase 1 — Core MVP (current)
- Hybrid Graph RAG (vector + knowledge graph, query-routed)
- Contextual Retrieval with Anthropic prompt caching
- Chunk-level + graph-node-level RBAC
- Decision Trail detection and graph integration
- SSO (SAML 2.0 / OIDC)
- Per-answer audit log (EU AI Act Article 13)
- File ingestion: PDF, DOCX, XLSX, PPTX, TXT, MD
- React frontend: Chat, Documents, Admin, Analytics

### Phase 1.5 — MCP Server + Agentic Execution
> Start only after Phase 1 adversarial RBAC tests all pass.

- **MCP Server** (`POST /mcp`, JSON-RPC 2.0): `search_knowledge`, `get_entity_relations`, `get_decisions`, `check_employee_access`
- **Agentic Execution**: post-answer action proposals (Jira, Slack, Calendar) with on-prem RBAC
- **Knowledge Health Monitor**: stale content, conflicting claims, coverage gaps, permission drift
- **Knowledge Graph Visualization**: force-directed graph page showing entities + Decision nodes

### Phase 2 — Connector Ecosystem
- Confluence (OAuth2 + REST API + webhooks, space/page-level ACL sync)
- Notion (OAuth2 + polling sync)
- Slack (Events API real-time + history ingest, thread-level chunking)
- Email / Calendar (IMAP + Google Calendar / Outlook, default confidential)
- File watcher (watchdog, monitor configured local directories)

### Phase 3 — Enterprise Maturity
- Kubernetes Helm chart (HPA for worker autoscaling, Qdrant cluster mode)
- GDPR data-subject export
- SOC 2 / EU AI Act audit log export (structured JSON/PDF)
- Proactive knowledge briefing (smart pre-meeting brief via calendar integration)
- Multi-LLM routing (route by query complexity / cost target)

---

## Ingestion Cost Model

With contextual retrieval enabled (Haiku + Anthropic prompt caching):

| Operation | Cost |
|---|---|
| Embedding (BGE-large local) | $0 |
| Reranking (local cross-encoder) | $0 |
| Contextual generation (Haiku + cache) | ~$0.09 / document (10k-token doc, 80 chunks) |
| Entity extraction (Haiku) | ~$0.05 / document |
| **Total per document** | **~$0.14** |
| **1,000 documents** | **~$140** |

For Ollama customers: $0 LLM cost (only electricity).

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

*Built with FastAPI, React, Qdrant, Apache AGE, and Claude.*
