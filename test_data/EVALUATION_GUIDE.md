# Company Brain — Evaluation Guide
## How to test every product feature after uploading the 5 test documents

---

## Upload Order and ACL Settings

Upload these files in order. Set the ACL as shown when uploading:

| File | Classification | Who Can See |
|---|---|---|
| 01_org_chart.md | internal | All authenticated users |
| 02_engineering_decisions.md | internal | All authenticated users |
| 03_product_roadmap_q3_2026.md | internal | All authenticated users |
| 04_q2_allhands_meeting_notes.md | internal | All authenticated users |
| 05_hr_compensation_bands.md | **confidential** | Admin + HR only |

---

## Test Suite

### GROUP 1 — Simple Fact Retrieval (Vector mode expected)
Test that basic questions return correct answers from the right document.

| # | Question | Expected Answer | Source Doc |
|---|---|---|---|
| 1 | Who is the CTO of NovaTech? | Daniel Okafor | 01_org_chart |
| 2 | Who leads the Platform team? | James Chen | 01_org_chart |
| 3 | What is Project Nova about? | AI answer quality improvements | 03_roadmap |
| 4 | What is NovaTech's ARR as of Q2 2026? | $1.2M | 04_meeting_notes |
| 5 | Who wrote the notes for the Q2 all-hands? | Grace Kimura | 04_meeting_notes |

**Pass criteria:** Answer is correct and cites the right source document.

---

### GROUP 2 — Decision Trail (Decision mode expected)
Test that the Decision Trail detects and surfaces engineering decisions.

| # | Question | Expected Answer | Source Doc |
|---|---|---|---|
| 6 | Why do we use PostgreSQL instead of MongoDB? | ACID, AGE graph extension, team expertise | 02_decisions |
| 7 | Why did we build our own LLM adapter instead of using LangChain? | LangChain had too many dependencies, 3 enterprise customers had Anthropic blocked | 02_decisions |
| 8 | Why do we use local embeddings instead of OpenAI? | Cost ($0 vs API fees), data sovereignty, BGE-large MTEB performance | 02_decisions |
| 9 | Why did we choose Qdrant over Pinecone? | Self-hosted, native BM25 hybrid, rich payload filtering for RBAC | 02_decisions |
| 10 | Why did we switch from Kuzu to Apache AGE for the knowledge graph? | Kuzu was archived Oct 2025; AGE runs inside Postgres, no extra container | 02_decisions |

**Pass criteria:** Answer includes the decision rationale and names who made the decision. Response shows `retrieval_mode: decision`.

---

### GROUP 3 — Multi-hop Relational (Hybrid/Graph mode expected)
Test that relationship questions use the knowledge graph correctly.

| # | Question | Expected Answer | Source Doc |
|---|---|---|---|
| 11 | Who works on both Project Titan and the Platform team? | James Chen leads both; Fatima Al-Rashid also on Platform/Project Shield | 01_org_chart + 03_roadmap |
| 12 | Which engineers report to Aisha Johnson? | Ryan Park, Elena Vasquez, Nate Wilson, Priyanka Desai | 01_org_chart |
| 13 | Who is responsible for the EMEA expansion? | Brandon Clark (Enterprise Sales) | 01_org_chart + 03_roadmap |
| 14 | What projects is Sophia Nguyen involved in? | Project Nova (AI answer quality), contextual retrieval work | 03_roadmap + 04_meeting_notes |
| 15 | Who is handling the SOC 2 compliance work? | Fatima Al-Rashid (Platform) with Anika Patel | 03_roadmap + 04_meeting_notes |

**Pass criteria:** Response shows `retrieval_mode: hybrid` or `graph`. Graph entities appear in `graph_entities_used`.

---

### GROUP 4 — RBAC Enforcement (Security tests)
Test that the permission system works correctly.

**Setup:** Create a test Employee user (role=employee, dept=engineering).

| # | Test | Steps | Expected Result |
|---|---|---|---|
| 16 | Basic RBAC block | Login as Employee user. Ask: "What is Sophia Nguyen's salary?" | Answer is empty or says "no information found". `denied_chunk_count > 0` |
| 17 | Confidential doc blocked | Login as Employee. Ask: "What are the engineering salary bands?" | No salary figures returned. Denial logged in access_audit |
| 18 | Non-confidential info visible | Login as Employee. Ask: "Who is on the AI/ML team?" | Correct answer (org chart is internal, visible to all) |
| 19 | Admin sees confidential | Login as Admin. Ask: "What is the base salary range for a Staff Engineer?" | Correct answer: $200K–$240K base |
| 20 | **Adversarial: graph node bleed** | Employee asks "Tell me about Sophia Nguyen." | Gets org chart info (her role, team). Does NOT get salary from the confidential doc. |

**Pass criteria:** Tests 16–17 return empty/denial. Tests 18–19 return correct info. Test 20 uses only the org chart data.

---

### GROUP 5 — Contextual Retrieval Quality
Test that context-free chunks are retrieved correctly due to contextual retrieval.

| # | Question | Why it's hard without contextual retrieval |
|---|---|---|
| 21 | What was decided about the SUPERSEDES decision chain? | "Moved from Q4 to Q3" in meeting notes — no project name in that sentence |
| 22 | What is the deadline was pushed in Q3 roadmap? | Various deadline references without document context |
| 23 | Who approved the ESOP refresh? | "Board approval: June 3, 2026" — no company name in that sentence |

**Pass criteria:** Correct answers retrieved despite context-free phrasing in source documents.

---

### GROUP 6 — Meeting Notes / Decision Detection
Test that decisions mentioned in meeting notes are captured.

| # | Question | Expected |
|---|---|---|
| 24 | What decision was made during the Q2 all-hands about the decision history feature? | SUPERSEDES visualization moved from Q4 to Q3; approved by Priya Sharma |
| 25 | Who was recognized for shipping contextual retrieval? | Sophia Nguyen — shipped from research paper to production in 3 weeks |
| 26 | What is NovaTech's fundraising plan? | Series A process starting Q4 2026, target $8-12M |
| 27 | What deal was the largest in company history? | Meridian Insurance — $180K ARR (Victoria Stone) |

---

## How to Verify the Knowledge Graph

After all 5 documents are indexed, run this query in Postgres:

```sql
-- Connect to Postgres
docker exec -it company-brain-postgres-1 psql -U brain -d company_brain

-- Load AGE
LOAD 'age';
SET search_path = ag_catalog, '$user', public;

-- Count all entities
SELECT * FROM cypher('company_brain', $$
  MATCH (n) RETURN labels(n)[0] as type, count(n) as count
$$) AS (type agtype, count agtype);
-- Expected: Person ~25+, Project ~5+, Team ~5+, Topic ~10+, Decision ~7+

-- See all decisions detected
SELECT * FROM cypher('company_brain', $$
  MATCH (d:Decision) RETURN d.title, d.confidence LIMIT 20
$$) AS (title agtype, confidence agtype);

-- See who works on what
SELECT * FROM cypher('company_brain', $$
  MATCH (p:Person)-[r:WORKS_ON]->(proj:Project)
  RETURN p.name, proj.name LIMIT 20
$$) AS (person agtype, project agtype);
```

---

## Evaluation Metrics

After running the test suite, score these dimensions:

| Metric | How to Measure | Target |
|---|---|---|
| **Fact Recall** (Group 1) | Questions with correct answer / total | 5/5 (100%) |
| **Decision Detection** (Group 2) | Decisions surfaced / decisions in docs | ≥ 5/5 (7 decisions in the docs) |
| **Graph Mode Activation** (Group 3) | Queries with `retrieval_mode: hybrid/graph` / total | ≥ 4/5 |
| **RBAC Enforcement** (Group 4) | Security tests passed / total | 5/5 (100%) — no exceptions |
| **Contextual Retrieval** (Group 5) | Context-free questions answered correctly | ≥ 2/3 |
| **Latency P50** | Median query latency | < 3s (first query loads model; subsequent < 2s) |

---

## A/B Test: Hybrid vs Vector-Only

To measure the graph retrieval improvement:

1. Set `GRAPH_ENABLED=false` in `.env`, restart backend
2. Run Group 3 questions, note answers and whether they mention relationship context
3. Set `GRAPH_ENABLED=true`, restart backend
4. Run the same Group 3 questions again, compare answers

The hybrid mode should give noticeably richer answers on questions 11–15 (the relationship questions).

---

## Real-World Data Sources for Extended Testing

Beyond the 5 sample files, these free public sources work well:

| Source | What You Get | URL |
|---|---|---|
| **SEC EDGAR** (10-K filings) | Real company decisions, org info, risk factors | sec.gov/edgar |
| **Anthropic / OpenAI research papers** | Technical decisions with rationale | arxiv.org |
| **Y Combinator company pages** | Startup descriptions, team info, products | ycombinator.com/companies |
| **Paul Graham essays** | Dense, thoughtful content, good for retrieval testing | paulgraham.com |
| **Wikipedia** | Entity-rich content, lots of relationships | en.wikipedia.org — export as PDF |
| **Your own company's Notion/Confluence export** | Real institutional memory | Export from your tool → upload as files |
