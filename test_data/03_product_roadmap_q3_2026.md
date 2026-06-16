# NovaTech Product Roadmap — Q3 2026
**Owner:** Sarah Lin (CPO), Carlos Rivera, Mei Zhang
**Status:** Approved
**Classification:** Internal
**Last Updated:** June 2026

---

## Q3 2026 Themes

1. **Enterprise Readiness** — SOC 2 Type II, SSO/SCIM, compliance exports
2. **Connector Ecosystem** — Slack real-time ingestion, Confluence bidirectional sync
3. **Answer Quality** — Contextual retrieval improvements, reranker upgrades
4. **Knowledge Graph** — Force-directed visualization, decision trail UI

---

## Project Titan — Enterprise Knowledge Graph Scaling

**Owner:** James Chen (Platform Team)
**Target:** August 2026
**Priority:** P0

**Problem:** At 500K+ entities, AGE graph queries are taking 800ms+ on depth-2 traversals. Enterprise customers with 5+ years of Confluence/Slack data will exceed this easily.

**Work:**
- Add GiST indexes on entity name columns in AGE graph
- Implement query result caching (Redis, TTL 5 minutes) for frequently-traversed entity subgraphs
- Batch MERGE operations for entity upsert (currently 1 entity per Cypher call)
- Profile AGE explain plans for slow queries — Fatima Al-Rashid leading profiling work

**Success metric:** Depth-1 subgraph traversal < 50ms at 2M entity nodes.

---

## Project Nova — AI Answer Quality Improvements

**Owner:** Dr. Marcus Liu, Sophia Nguyen (AI/ML Team)
**Target:** July 2026
**Priority:** P0

**Problem:** Answer quality drops on multi-hop questions that span more than 2 documents. The graph traversal finds the entities but the LLM prompt ordering affects reasoning quality.

**Work:**
- Upgrade cross-encoder reranker from MiniLM-L-6 to MiniLM-L-12 (better quality, 1.8x slower)
- Implement parent-chunk context expansion: when a child chunk is retrieved, automatically include its parent section in the LLM context
- A/B test contextual retrieval vs. raw chunks on the golden Q&A set
- Build eval harness: Recall@5, Recall@10, NDCG@10, LLM-judge (GPT-4o) correctness scoring
- Omar Hassan owns the evaluation framework

**Success metric:** Recall@10 > 0.85 on multi-hop golden Q&A set. LLM-judge score > 4.0/5.0.

---

## Project Connect — Slack + Confluence Connectors

**Owner:** Elena Vasquez (Product Engineering), Tobias Brown (PM)
**Target:** September 2026
**Priority:** P1

**Problem:** 80% of company knowledge lives in Slack threads and Confluence pages, not files. File upload is a band-aid.

**Work:**
- **Slack connector:** OAuth2 app installation, Events API (real-time new messages), history ingest of existing channels with configurable lookback (default 1 year). Thread = chunking unit. Private channel membership = ACL.
- **Confluence connector:** OAuth2 REST API, space/page crawler, webhook on page create/update/delete. Space permissions → `allowed_departments`. Page restrictions → `allowed_users`.
- Nate Wilson owns Confluence; Priyanka Desai owns Slack mobile notification syncing

**Success metric:** 3 beta customers have Slack + Confluence connected and report no missing results on questions about content they know was discussed in those tools.

---

## Project Shield — SOC 2 Type II Compliance

**Owner:** Fatima Al-Rashid (Platform), Anika Patel (HR)
**Target:** October 2026
**Priority:** P1

**Problem:** Enterprise sales deals are blocked pending SOC 2 Type II certification. Three deals in Q2 stalled at security review.

**Work:**
- Access audit log → structured JSON export (GDPR + SOC 2 artifact)
- EU AI Act Article 13 compliance report generation (per-answer traceability)
- Encryption at rest: Postgres data directory + Qdrant storage volume (LUKS or cloud-managed)
- Secret rotation: JWT secrets, DB passwords via automated rotation
- Penetration test with Trail of Bits (scheduled: August 2026)

**Success metric:** SOC 2 Type II report issued. EU AI Act Article 13 compliance documentation complete.

---

## Knowledge Graph Visualization (Mini-Feature)

**Owner:** Ryan Park (Product Engineering), Anika Osei (Design)
**Target:** July 2026 (internal demo), August 2026 (GA)
**Priority:** P2

**Problem:** The knowledge graph is our biggest differentiator but nobody can see it. Demos need a visual wow moment.

**Work:**
- New `/graph` page using react-force-graph library
- Node types rendered differently: Person (circle), Project (square), Team (diamond), Decision (hexagon — gold color)
- Click on a Decision node → show decision detail panel (summary, made by, alternatives, evidence chunks)
- Filter by entity type, date range, department
- Respects RBAC — only shows entities the current user can access

**Success metric:** Sales team reports the graph visualization accelerates demo-to-POC conversion.

---

## Deferred to Q4 2026

- **Proactive knowledge briefing** — Pre-meeting smart brief pushed to Slack (requires Calendar connector)
- **SCIM provisioning** — Auto-provision/deprovision users from IdP (Okta, Azure AD)
- **Multi-LLM routing** — Route queries to different models by complexity/cost target
- **Helm chart** — Kubernetes Helm chart for enterprise self-hosted deployment

---

## Q3 2026 Key Metrics

| Metric | Q2 2026 Actual | Q3 2026 Target |
|---|---|---|
| Active enterprise customers | 4 | 10 |
| Avg documents indexed per customer | 2,400 | 8,000 |
| Avg daily queries per customer | 85 | 300 |
| Answer satisfaction rate (thumbs up) | 71% | 82% |
| Recall@10 (multi-hop golden set) | 0.68 | 0.85 |
| Median query latency (P50) | 1,240ms | 900ms |
| P95 query latency | 4,800ms | 2,500ms |
