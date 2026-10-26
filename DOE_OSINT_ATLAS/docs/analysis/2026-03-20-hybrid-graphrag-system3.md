# System 3 Analysis: Hybrid GraphRAG for DOE Contracts
Date: 2026-03-20

## Context (Phase 0)

**Existing assets:**
- 250,125 DOE contract transactions in SQLite (18 columns, 143 MB)
- 247,819 ChromaDB embeddings (all-MiniLM-L6-v2, 384-dim, 282 MB)
- Working CLI RAG chatbot (chat_with_contracts.py) — semantic search only
- ContractDataStore gateway with 3 methods: query_sql, search_semantic, search_text
- NetworkX 2.6.3 and FastAPI 0.115.6 already installed but unused
- Ollama running locally with dolphin3 model
- Rich structured entities in data: recipients, agencies, sub-agencies, states, cities, NAICS codes, PSC codes, award types

**Unknown:**
- Dolphin3's quality for entity extraction from transaction descriptions
- Memory footprint of full entity graph at 250K scale
- User's GraphRAG depth expectations (full Microsoft-style vs. structured graph)

## Problem Frame (Phase 1)

**Stated three ways:**
1. Build a web-based knowledge graph explorer + RAG chatbot fusing vector, keyword, and graph retrieval
2. Replace the CLI with a visual network analysis tool for following-the-money across contractors, agencies, and research areas
3. Create a GraphRAG system modeling DOE contracting entities as a navigable knowledge graph with hybrid retrieval

**Assumptions:**
1. Graph from structured fields (recipient, agency, NAICS) — not LLM extraction from descriptions
2. igraph preferred over NetworkX for 250K-node performance (C core vs pure Python)
3. In-memory graph adequate (no Neo4j)
4. SvelteKit frontend → FastAPI backend architecture
5. Filtered subgraph visualization (browsers can't render 250K nodes)
6. Dolphin3 handles query-time entity recognition, not bulk extraction
7. Community detection (Leiden) adds value for topic clustering
8. Reuse existing SQLite + ChromaDB, add graph layer alongside
9. Hybrid = vector (ChromaDB) + keyword (SQLite FTS5) + graph (neighborhood traversal)
10. Entity-relationship topology, not a graph database

## Perspectives (Phase 2)

### Skeptic
Real GraphRAG needs community summaries and multi-hop reasoning. Dolphin3 is a smaller model. Maybe the user just wants network visualization + better search. Challenges assumption #7 (community detection value) — without good summaries, communities are just clusters.

### Intelligence Analyst (Outsider)
In link analysis, the value is "follow the money." Show a contractor → every agency they work with → every co-contractor on the same awards → every location. The graph IS the interface. Chat is secondary. Challenges assumption #4 — the frontend should be graph-first, not chat-first.

### Historian
The codebase works. Each added layer multiplies failure modes. Build incrementally: keyword search first, then structured graph, then community detection. Challenges the implicit assumption that everything should be built at once.

### Futurist
Design modular interfaces. igraph today, Neo4j tomorrow. The retrieval fusion API should be backend-agnostic. Challenges assumption #3 — in-memory is fine NOW but design for swap-ability.

### Advocate (DOE Analyst)
"Who are the top fusion energy contractors and what's their network?" — wants visual map with dollar amounts on edges, click to drill down, text summary. Both visual exploration AND natural language. Challenges nothing — this IS the requirement.

### Conflicts & Agreements
- **Agreement:** Graph from structured fields first (cheap, reliable). Filtered subgraph viz. Preserve existing stores.
- **Conflict:** Skeptic ("keep simple") vs. Advocate ("full interactive"). Resolution: structured graph + community detection (algorithmic, no LLM needed), defer LLM entity extraction.
- **Conflict:** Historian ("incremental") vs. full build. Resolution: phased architecture where each layer works independently.

## Creative Reframes (Phase 3)

### Restaurant Analogy
Dishes share ingredients. Search by flavor (vector), ingredient name (keyword), or "pairs well with" (graph). User searches "battery research" → semantic matches (vector) + exact matches (keyword "battery") + network expansion (other contracts from same recipients/NAICS codes).

### Pre-mortem
Failed because: (1) 250K in-memory graph exhausted RAM, (2) hybrid fusion poorly tuned — graph results diluted vector results, (3) UI was beautiful but users didn't know what to click.
**Mitigation:** igraph (C core, memory-efficient), tunable fusion weights, clear UI entry points.

### Inversion (MVP Fallback)
Skip the knowledge graph entirely. Add keyword search + faceted filtering + network visualization of search results. 80% value, 20% effort. The structured entity graph is a layer ON TOP of this.

## Meta-Cognitive Audit (Phase 4)

| Dimension | Score | Evidence |
|-----------|-------|---------|
| Problem definition | 4/5 | Clear task, resolved GraphRAG depth question |
| Assumption validity | 3/5 | igraph vs NetworkX needs verification; Dolphin3 capability is a risk |
| Perspective diversity | 4/5 | Five genuine perspectives, real disagreements |
| Creative exploration | 4/5 | Pre-mortem and inversion produced actionable insights |
| Bias awareness | 3/5 | Complexity bias mitigated by phased approach |

### Active Biases Identified
- **Complexity bias:** Wanting full Microsoft GraphRAG when structured graph suffices. Mitigated by phased architecture.
- **Anchoring:** On GraphRAG terminology. Mitigated by focusing on user value (follow-the-money, visual exploration).

## Synthesis & Recommendation

### Architecture: Three-Tier Hybrid GraphRAG

**Layer 1 — Data Stores (existing + new):**
- SQLite: Structured queries, keyword search (upgrade LIKE → FTS5)
- ChromaDB: Semantic vector search (existing, 247K embeddings)
- igraph: In-memory knowledge graph (NEW) with persistence via pickle/GraphML

**Layer 2 — Knowledge Graph Construction:**
- **Nodes:** Recipients (~5K unique), Agencies (~50), Sub-Agencies (~100), States (~55), NAICS codes (~500), PSC codes (~1K)
- **Edges:** Contracts connecting entities (weighted by total dollar obligation)
- **Community detection:** Leiden algorithm on igraph (fast, algorithmic, no LLM needed)
- **Pre-computed at ingestion time**, not query time

**Layer 3 — Hybrid Retrieval Pipeline:**
```
User Query
  ├── 1. Vector Search (ChromaDB) → top-K contracts by semantic similarity
  ├── 2. Keyword Search (SQLite FTS5) → contracts matching exact terms
  └── 3. Graph Search (igraph) → entity identification → 1-2 hop traversal → related contracts
       └── Community context: which community does the entity belong to?

Fusion: Reciprocal Rank Fusion (RRF) with tunable weights
  → Combined context → Dolphin3 via Ollama → Streamed response
```

**Backend:** FastAPI with SSE streaming
- `POST /api/chat` — hybrid RAG with streaming response
- `GET /api/graph?entity=X&hops=2` — subgraph retrieval for visualization
- `GET /api/search?q=X&mode=hybrid` — search without chat
- `GET /api/communities` — list detected communities with summaries
- `GET /api/stats` — aggregate statistics

**Frontend:** SvelteKit 2 (Svelte 5) with:
- **Graph panel:** force-graph (Canvas-based) for interactive subgraph exploration
- **Chat panel:** streaming RAG interface
- **Search/filter panel:** keyword + faceted filtering
- **Detail panel:** contract details on node/edge click

**Graph Node Budget:** ~7K nodes (recipients + agencies + states + NAICS + PSC), not 250K. Contracts are edges, not nodes. This is very manageable for in-browser rendering.

### Key Design Decisions
1. **igraph over NetworkX:** C core gives millisecond BFS at scale. NetworkX would be seconds.
2. **Structured graph over LLM extraction:** 18 structured columns provide clean entity data. LLM extraction from Dolphin3 would be noisy and slow across 250K records.
3. **Contracts as edges, not nodes:** A contract connects a recipient to an agency in a location in a NAICS sector. This gives a natural multi-partite graph.
4. **Community detection without LLM summaries:** Leiden communities identify clusters. Summaries can be added later with Dolphin3 if needed.
5. **FastAPI → SvelteKit proxy:** SvelteKit API routes proxy to FastAPI. Single origin, no CORS.
6. **SSE for streaming:** Ollama NDJSON → FastAPI re-streams as SSE → browser EventSource.

## Blind Spots & Uncertainties
1. **Dolphin3 quality:** May struggle with entity recognition in queries (e.g., mapping "battery research" to NAICS codes). Fallback: keyword matching against known entity names.
2. **Graph density:** If top 5 national labs connect to everything, the graph may be a star topology with little structure. Community detection helps, but visualization may need filtering by dollar threshold.
3. **FTS5 migration:** Upgrading from LIKE to FTS5 requires re-ingestion or virtual table creation. May add complexity.
4. **SvelteKit + Python:** Two servers to manage. Could be simplified with Docker Compose or a single process manager.
5. **Embedding model mismatch:** ChromaDB uses all-MiniLM-L6-v2 (SentenceTransformer). If we switch to Ollama embeddings for consistency, we'd need to re-embed 247K records.
