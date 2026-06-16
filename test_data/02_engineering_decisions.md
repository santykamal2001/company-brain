# NovaTech Engineering Decision Log
**Owner:** Daniel Okafor (CTO)
**Maintained by:** Platform Team
**Classification:** Internal
**Last Updated:** June 2026

This document records major architectural and technology decisions made by the NovaTech engineering team. Each entry includes the context, decision, who made it, alternatives that were considered, and the rationale.

---

## DEC-001: Primary Database — PostgreSQL over MongoDB
**Decided:** January 2024
**Decided by:** Daniel Okafor, James Chen, Luis Torres
**Status:** Active

**Decision:** We chose PostgreSQL as our primary database instead of MongoDB.

**Context:** At founding, we needed to pick a primary data store. The team had experience with both document databases and relational databases. Most early startup data was document-like (JSON configs, user profiles, flexible schemas).

**Alternatives considered:**
- MongoDB — flexible schema, native JSON, easier horizontal scaling at low data volumes
- DynamoDB — fully managed, AWS-native, no ops burden
- CockroachDB — distributed SQL, strong consistency, Postgres-compatible
- PostgreSQL — ACID, mature, strong ecosystem, extensions (especially Apache AGE for graph data)

**Rationale:** PostgreSQL won because of three factors: (1) We knew we'd need graph capabilities for the knowledge graph feature — Apache AGE runs inside Postgres with no extra container; (2) Our compliance requirements (SOC 2, eventually EU AI Act) needed ACID transactions and strong audit guarantees; (3) Luis Torres had deep Postgres expertise and could tune it from day one. MongoDB's flexible schema was a liability at scale — schema drift caused two production incidents at previous companies team members had worked at.

**Outcome:** Still using Postgres in 2026. The AGE graph extension has been critical for the Decision Trail feature. Would make the same choice again.

---

## DEC-002: LLM Provider Strategy — Multi-Provider Adapter Pattern
**Decided:** March 2024
**Decided by:** Dr. Marcus Liu, Daniel Okafor, Priya Sharma
**Status:** Active

**Decision:** We built a provider-agnostic LLM adapter layer from day one rather than coupling directly to any single LLM provider.

**Context:** In early 2024, Claude 3, GPT-4 Turbo, and Gemini Pro were all competitive. Our enterprise customers needed to run models on-premise (Ollama) for data sovereignty reasons. We needed to avoid vendor lock-in.

**Alternatives considered:**
- Direct Anthropic API coupling — simpler code, better prompt caching integration
- LangChain abstraction — ecosystem support, many connectors, but heavy dependency, frequent breaking changes
- Direct OpenAI coupling — largest ecosystem, most community support
- Build our own adapter — full control, no dependency risk

**Rationale:** We built our own thin adapter (claude | openai | azure | ollama, same interface: `complete()`, `complete_with_cache()`, `complete_json()`). LangChain was rejected because it introduced too many transitive dependencies and abstracted things we needed to control (prompt caching, tool-use streaming). Direct coupling to any single provider would have blocked enterprise deals — three of our first five enterprise prospects had Anthropic blocked by security policy.

**Outcome:** The adapter has let us switch extraction tasks to Haiku (10x cheaper than Sonnet) while keeping answer generation on Sonnet. Saved ~$4,000/month at current query volume.

---

## DEC-003: Embedding Model — Local BGE-large vs. OpenAI Ada
**Decided:** April 2024
**Decided by:** Sophia Nguyen, Dr. Marcus Liu
**Status:** Active

**Decision:** We use BAAI/bge-large-en-v1.5 running locally via sentence-transformers instead of OpenAI's text-embedding-ada-002 or text-embedding-3-large.

**Context:** Embedding is the highest-volume API call in a RAG system. Every chunk of every document gets embedded at ingestion time. At 1M chunks across our customer base, API costs compound fast.

**Alternatives considered:**
- OpenAI text-embedding-ada-002 — $0.10/1M tokens, widely used, zero infra overhead
- OpenAI text-embedding-3-large — higher quality, $0.13/1M tokens, still external API
- Cohere embed-v3 — competitive quality, flexible input types
- BAAI/bge-large-en-v1.5 — 1024-dim, best-in-class on MTEB benchmarks, runs locally, $0 per embedding

**Rationale:** Local embeddings won on three dimensions: (1) Cost — $0 vs $0.10-0.13/1M tokens; at our ingestion volume this saves ~$2,000/month; (2) Data sovereignty — embeddings never leave the customer's network, which is a hard requirement for financial and legal customers; (3) Quality — BGE-large-en-v1.5 outperforms ada-002 on MTEB benchmarks as of 2024 at the time of decision.

**Outcome:** Zero embedding API cost. GPU acceleration with CUDA when available (2-3x faster on GPU nodes). The model is downloaded once to the Docker volume and reused.

---

## DEC-004: Vector Store — Qdrant over Pinecone and Weaviate
**Decided:** April 2024
**Decided by:** Sophia Nguyen, James Chen, Elena Vasquez
**Status:** Active

**Decision:** We use Qdrant (self-hosted) as our vector store instead of Pinecone (managed SaaS) or Weaviate.

**Alternatives considered:**
- Pinecone — fully managed, zero ops, excellent developer experience, but SaaS-only, data leaves customer network, $70+/month at scale
- Weaviate — self-hostable, strong filtering, but resource-heavy, complex setup
- pgvector (Postgres extension) — same container as main DB, zero extra infra, but limited filtering capabilities and slower at high vector counts
- Qdrant — self-hosted, excellent metadata filtering, native BM25 sparse vectors, fast, Apache 2.0 license

**Rationale:** Qdrant was the only option that combined: (1) Self-hosted so data stays on-premise; (2) Native hybrid search (dense + sparse BM25 in one query) without a separate infrastructure component; (3) Rich payload filtering — we needed to filter by role, department, and ACL version on every query without a hot-path Postgres join; (4) Apache 2.0 license — no commercial licensing risk for customers.

**Outcome:** Qdrant's payload indexing has been critical for RBAC pre-filtering. We create payload indexes on `allowed_role_*` and `no_dept_restriction` at collection creation time — queries with ACL filters run at full speed.

---

## DEC-005: Background Jobs — Celery + Redis over FastAPI BackgroundTasks
**Decided:** May 2024
**Decided by:** Luis Torres, Elena Vasquez
**Status:** Active

**Decision:** We use Celery with Redis as the broker for all background ingestion work instead of FastAPI's built-in BackgroundTasks.

**Alternatives considered:**
- FastAPI BackgroundTasks — zero extra infrastructure, runs in the same process
- Python RQ (Redis Queue) — simpler than Celery, Redis-backed, good for simple queues
- Celery + Redis — mature, battle-tested, retry logic, task routing, monitoring via Flower
- AWS SQS + Lambda — fully managed, but cloud-only (defeats self-hosted goal)

**Rationale:** Document ingestion is an 11-step pipeline that can take 30–120 seconds per document (OCR, embedding, entity extraction, graph upsert). FastAPI BackgroundTasks run in the web worker process — a crashed worker kills in-flight ingestion tasks. Celery workers are separate processes with configurable concurrency, retry logic, and visibility into queue depth. We also needed to be able to scale workers independently from web servers.

**Outcome:** The worker runs at concurrency=4 by default. Large document batches (100+ files) queue correctly and complete reliably. Task retry on transient Anthropic API errors (429 rate limit) works out of the box.

---

## DEC-006: Knowledge Graph Store — Apache AGE (Postgres extension) over Neo4j
**Decided:** October 2025 (replacing Kuzu which was archived)
**Decided by:** Daniel Okafor, Sophia Nguyen, Dr. Marcus Liu
**Status:** Active

**Decision:** We use Apache AGE (a Postgres extension) for the knowledge graph instead of Neo4j or a dedicated graph database.

**Context:** We originally selected Kuzu (an embedded graph database written in C++) but it was archived in October 2025 and is no longer maintained. We needed to migrate.

**Alternatives considered:**
- Neo4j Community Edition — Cypher-compatible, mature, excellent tooling, but requires a separate container, separate backup/monitoring, and has commercial licensing restrictions
- Amazon Neptune — managed, no ops, but cloud-only
- TigerGraph — enterprise-grade, but expensive and complex
- Apache AGE — Postgres extension (Apache 2.0), Cypher-compatible, runs INSIDE the existing Postgres container, no extra infrastructure

**Rationale:** Apache AGE won because it runs as a Postgres extension — meaning: (1) No extra container, no extra backup, no extra monitoring toolchain; (2) Same connection pool as the rest of the backend; (3) Cypher query language (same syntax we already used with Kuzu); (4) In production at Trendyol (large e-commerce platform) as of 2026; (5) Apache 2.0 license with no commercial restrictions. The trade-off is that AGE's Cypher support is a subset of Neo4j's — but our access pattern (depth-1 subgraph traversal anchored on entity names) is well within AGE's capabilities.

**Outcome:** Single `CREATE EXTENSION IF NOT EXISTS age;` in the Alembic migration. Graph and relational data in the same Postgres instance — same transaction boundary, same backup, same failover.

---

## DEC-007: Frontend Framework — React + Vite over Next.js
**Decided:** June 2024
**Decided by:** Ryan Park, Aisha Johnson
**Status:** Active

**Decision:** We use React + Vite (SPA) for the frontend instead of Next.js (SSR/SSG).

**Alternatives considered:**
- Next.js — SSR for SEO, file-based routing, Vercel integration, large ecosystem
- Remix — SSR, progressive enhancement, great for forms
- SvelteKit — faster runtime, smaller bundle, but smaller talent pool
- React + Vite (SPA) — fast dev server, simple build, easy to containerize with nginx

**Rationale:** Company Brain is an authenticated web app — no public pages that need SEO. SSR complexity (hydration, server components, edge functions) adds deployment complexity for what is essentially an enterprise dashboard. A Vite SPA builds to a static bundle that nginx serves, making it trivially containerizable. The Vite dev server's /api proxy setup means frontend and backend can develop independently. Ryan Park had 4 years of React experience vs. 6 months of Next.js, so iteration speed mattered.

**Outcome:** Build time: ~8 seconds. Bundle size: ~180KB gzipped. nginx serving the SPA + proxying /api routes to the backend container works perfectly in Docker Compose and will work in Kubernetes with an ingress controller.
