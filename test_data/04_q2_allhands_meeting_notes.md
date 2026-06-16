# Q2 2026 All-Hands Meeting Notes
**Date:** June 5, 2026
**Location:** NovaTech HQ, San Francisco + Zoom
**Facilitator:** Priya Sharma (CEO)
**Note-taker:** Grace Kimura
**Attendees:** All NovaTech staff (38 people)
**Classification:** Internal

---

## Opening — Priya Sharma

Priya opened by acknowledging Q2 was a breakout quarter. We closed 4 enterprise deals, doubled ARR, and shipped the Decision Trail feature — the thing that's now showing up in every sales call as the "wow moment."

She noted that the team grew from 24 to 38 people in Q2 and asked everyone to be deliberate about knowledge transfer as the company scales. "We're building a product that solves institutional memory loss — we'd better not suffer from it ourselves."

---

## Q2 Metrics Review — Marcus Webb (CRO)

- **ARR:** $1.2M (up from $580K at start of Q2) — 107% growth quarter-over-quarter
- **New enterprise deals closed:** 4 (Meridian Insurance, Apex Capital, LegalEdge LLP, Greenfield Health)
- **Pipeline:** 18 active enterprise deals, $4.2M total pipeline
- **Deal blockers:**
  - SOC 2 Type II missing — blocked 3 deals in Q2 (now P1 in Q3 roadmap per Project Shield)
  - Slack connector missing — mentioned by 11 of 18 active pipeline deals

Marcus noted that Glean's $220M Series E (March 2026) has increased awareness in the market — "We're being pulled into deals because prospects want a self-hosted, auditable alternative."

---

## Engineering Update — Daniel Okafor (CTO)

**Shipped in Q2:**
- Decision Trail: LLM-based decision detection with >0.75 confidence threshold, Decision nodes in AGE graph, query routing to Decision mode on "why/who decided/rationale" questions
- Contextual Retrieval: Anthropic prompt caching, 49% reduction in retrieval failure on internal golden set
- RBAC chunk-level enforcement: Qdrant pre-filter + Postgres post-filter defense-in-depth
- EU AI Act Article 13 audit trail: per-answer access_audit record with chunk provenance

**Upcoming in Q3 (Project Titan + Nova):**
- Graph query performance: targeting <50ms depth-1 traversal at 2M entities
- Reranker upgrade: MiniLM-L-6 → MiniLM-L-12
- Eval harness shipping July (Sophia Nguyen leading)

Daniel flagged one technical risk: "The Slack connector is more complex than we thought. Slack's Rate Limit Tier 3 means we can only fetch ~50 messages/minute per workspace during history ingest. Large Slack workspaces (100k+ messages) will take hours to ingest. We're building a batched catch-up mode."

---

## Product Update — Sarah Lin (CPO)

Sarah presented the Q3 roadmap (see roadmap doc). Key callouts:
- The force-directed graph visualization is the #1 demo request from sales. Ryan Park will ship a prototype by July 15.
- Carlos Rivera is leading a customer discovery sprint in June — 10 interviews with current customers to prioritize Q4 features.
- User satisfaction on the Decision Trail feature is 4.3/5 based on 47 survey responses. Most common piece of feedback: "The answers are good but I want to see the decision history chain — what superseded what."

**Decision made during meeting:** Sarah, Carlos, and Mei agreed to move the SUPERSEDES decision chain visualization to the Q3 graph page (previously planned for Q4). Rationale: The customer feedback is strong enough and Ryan can build it alongside the graph visualization work. This decision was approved by Priya Sharma.

---

## People Update — Anika Patel (VP People)

- **New hires in Q2:** 14 (6 engineering, 3 sales, 2 customer success, 2 marketing, 1 HR)
- **Q3 headcount plan:** Hiring 8 more (4 engineering, 2 sales, 1 CSM, 1 recruiter)
- **Open roles:**
  - Senior Backend Engineer (Python, FastAPI) — Aisha Johnson's team
  - Senior ML Engineer (RAG, embeddings) — Marcus Liu's team
  - Enterprise AE (EMEA expansion) — Brandon Clark's territory
  - Senior CSM (Jordan Thompson's team)
- Anika announced NovaTech's first ESOP refresh — all employees with >12 months tenure will receive additional options. Details to follow by email.
- Remote-first policy updated: minimum 1 HQ visit per quarter for all employees, with travel covered.

---

## Finance Update — Priya Sharma

- **Runway:** 26 months at current burn
- **Q2 burn rate:** $380K/month (down from $420K after cloud cost optimizations by Kofi Mensah)
- **Q3 plan:** Targeting profitability on new deals (unit economics positive since April)
- Priya noted that the board approved a Series A process starting Q4 2026. Target raise: $8–12M. "We're not raising because we need cash — we're raising to accelerate the Slack connector, SOC 2, and Europe expansion."

---

## Team Recognition

Priya recognized the following team members:
- **Sophia Nguyen** — Shipped contextual retrieval from research paper to production in 3 weeks
- **Kofi Mensah** — Reduced infrastructure costs by $40K/month through Kubernetes right-sizing
- **Victoria Stone** — Closed the Meridian Insurance deal (largest deal in company history: $180K ARR)
- **Mei Zhang** — Decision Trail PM — "The feature that customers talk about in every demo"

---

## Q&A Highlights

**Q (Nate Wilson): "Will the Slack connector support private channels?"**
A (Daniel Okafor): "Yes, but privacy is enforced — only the Slack workspace admin can authorize ingestion of private channels, and only members of the channel at the time of ingestion can query those messages. We inherit Slack's channel membership as the ACL."

**Q (Nalini Singh): "When will we have a EMEA data residency option?"**
A (Priya Sharma): "The EU data residency option will come with the K8s Helm chart and Terraform modules — we're targeting Q1 2027. In the meantime, enterprise customers can self-host on EU cloud infrastructure today using our Docker Compose setup."

**Q (Lucia Reyes): "Can we publish case studies from Q2 customers?"**
A (Marcus Webb): "Meridian Insurance and Greenfield Health have agreed to named case studies. LegalEdge and Apex want to stay anonymous for now. We're targeting a Meridian case study for the company blog in July."

---

## Action Items

| Action | Owner | Due |
|---|---|---|
| Ship graph visualization prototype | Ryan Park | July 15, 2026 |
| Add SUPERSEDES chain to graph page (moved from Q4) | Ryan Park | August 2026 |
| Send ESOP refresh details to all employees | Anika Patel | June 12, 2026 |
| Schedule 10 customer discovery interviews | Carlos Rivera | June 2026 |
| Publish Meridian Insurance case study | Lucia Reyes | July 2026 |
| Start SOC 2 audit prep with auditor | Fatima Al-Rashid | June 2026 |
| Share Series A preparation timeline with board | Priya Sharma | July 2026 |

---

*Notes distributed to all staff via email. Recording available in the company Google Drive folder.*
