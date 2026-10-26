# Design: DOE Contract GraphRAG — Process Intelligence Tool
Date: 2026-03-20

## Overview

A hybrid vector + keyword + graph RAG system for exploring DOE contract data, with a focus on answering "how does DOE make X?" questions by discovering and synthesizing manufacturing process chains from contract records.

**Stack:** FastAPI (Python) + SvelteKit (static build) + igraph + ChromaDB + SQLite + Ollama (Dolphin3)
**Deployment:** Docker container with configurable Ollama target (host Metal GPU or containerized)
**Data:** 250,125 DOE contract transactions (FY2007-2026), $643.8B total

## 1. System Architecture

Single Docker container running FastAPI, serving the SvelteKit static build and all API endpoints. Ollama runs on the host (macOS Metal GPU) or optionally in a companion container (Linux GPU).

```
┌──────────────────────────────────────────────┐
│  Docker Container                             │
│                                               │
│  FastAPI Server (port 8000)                   │
│  ├── Static files: SvelteKit build            │
│  ├── /api/chat      (hybrid RAG + SSE)        │
│  ├── /api/recipe    (deep research + SSE)     │
│  ├── /api/graph     (subgraph queries)        │
│  ├── /api/search    (hybrid search)           │
│  │                                            │
│  ├── Graph Engine (igraph + Leiden)           │
│  ├── Hybrid Retriever (vector+kw+graph)       │
│  └── Recipe Engine (multi-query agentic)      │
│                                               │
│  Volumes:                                     │
│  /data/doe_contracts.db (SQLite)              │
│  /data/chroma_db/ (ChromaDB)                  │
│  /data/graph.pkl (igraph pickle)              │
│  /data/topics.db (extracted topics)           │
└───────────────────┬──────────────────────────┘
                    │
         OLLAMA_HOST (configurable)
         default: host.docker.internal:11434
                    │
             ┌──────┴──────┐
             │   Ollama    │
             │  (dolphin3) │
             └─────────────┘
```

**Docker Compose:**
- `docker compose up` starts the app container
- Env var `OLLAMA_HOST` switches between host Ollama (macOS Metal) and containerized Ollama (Linux GPU)
- Multi-stage Dockerfile: Node.js stage builds SvelteKit, Python stage runs FastAPI
- Volumes mount data files (not copied into image)

## 2. Knowledge Graph Model

This is a **multi-partite entity graph**, NOT a graph where contracts are nodes. Individual contracts are the raw data; edges are **aggregations** over contracts connecting entity pairs. For example, if Sandia has 200 contracts under PSC "Nuclear Weapons Modernization", there is ONE edge between the Sandia node and that PSC node, weighted by the sum of those 200 contracts' dollar obligations.

### Node Types

| Type | Source | ~Count | Attributes |
|------|--------|--------|------------|
| **Recipient** | `recipient_name` | 5,000 | name, state, city, total_obligated |
| **PSC** | `product_or_service_code_description` | 1,000 | description |
| **NAICS** | `naics_description` | 500 | description |
| **Topic** | LLM-extracted from `transaction_description` | TBD | name, description, source_contract_ids |

Note: `build_graph.py` queries SQLite directly (not through `ContractDataStore`) to access all 18 ingested columns including `recipient_city_name` and `primary_place_of_performance_state_name`.

### Edge Types

| Edge | Meaning | Weight | Construction |
|------|---------|--------|-------------|
| Recipient ↔ PSC | "Sandia does Nuclear Weapons Modernization" | Sum of $ obligations | `GROUP BY recipient_name, product_or_service_code_description` |
| Recipient ↔ NAICS | "Sandia works in R&D Physical Sciences" | Sum of $ obligations | `GROUP BY recipient_name, naics_description` |
| Recipient ↔ Topic | "Sandia does garnet ceramic fabrication" | Contract count + $ | Join via `topics.db` source contract IDs |
| PSC ↔ NAICS | Co-occurrence in same contracts | Contract count | `GROUP BY product_or_service_code_description, naics_description` |
| Recipient ↔ Recipient | Shared PSC/NAICS/Topic (capability overlap) | Jaccard similarity | **Deferred to v2.** O(n²) over 5K recipients; requires minimum Jaccard threshold (0.1) and is not needed for v1 process chain discovery. |

### Community Detection

- Leiden algorithm on the full graph (via `leidenalg` package)
- Communities represent capability clusters (e.g., "nuclear weapons complex", "energy storage R&D", "environmental cleanup")
- Stored as node attributes for filtering and context

### topics.db Schema

```sql
CREATE TABLE topics (
    topic_id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_name TEXT NOT NULL,           -- e.g., "solid electrolyte fabrication"
    topic_description TEXT,             -- longer description from LLM
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE topic_contracts (
    topic_id INTEGER REFERENCES topics(topic_id),
    contract_key TEXT NOT NULL,         -- contract_transaction_unique_key
    confidence REAL DEFAULT 1.0,        -- LLM extraction confidence
    PRIMARY KEY (topic_id, contract_key)
);

CREATE INDEX idx_topic_name ON topics(topic_name);
CREATE INDEX idx_topic_contract ON topic_contracts(contract_key);
```

### Construction & Lifecycle

- **Structured graph** (Recipients + PSC + NAICS): Built from SQLite by `build_graph.py`. Fast (~seconds).
- **Topic layer**: Built incrementally via LLM extraction by `extract_topics.py`. Stored in `topics.db`.
- **Persistence**: igraph pickle file (`graph.pkl`) for fast reload.
- **Graph is immutable at runtime.** The FastAPI server loads `graph.pkl` into memory at startup and serves it read-only. After running `extract_topics.py` or `build_graph.py`, the container must be restarted (or send `SIGHUP`) to reload the updated graph. This avoids concurrency issues between graph reads and writes.

## 3. Hybrid Retrieval Pipeline

### Normal Chat Mode

When user asks a question:

1. **Parallel retrieval** (all 3 fire via asyncio):
   - **Vector**: ChromaDB semantic search using `all-MiniLM-L6-v2` embeddings (top 20). This model MUST match the one used in `ingest_to_chroma.py`. Changing it requires re-embedding all 247K records.
   - **Keyword**: SQLite FTS5 full-text search on `transaction_description` (top 20). **Fallback**: if FTS5 virtual table is not ready, falls back to `LIKE`-based search via `ContractDataStore.search_text()`.
   - **Graph**: Match query entities to graph nodes → 1-2 hop traversal → connected contracts

2. **Fusion**: Reciprocal Rank Fusion (RRF) across all sources
   - `score(doc) = Σ 1/(k + rank_source)` where k=60
   - Each result tagged with source(s): vector, keyword, graph

3. **Context assembly**: Top 15 fused results formatted as context for Dolphin3

4. **LLM response**: Dolphin3 via Ollama `/api/chat` (streamed as SSE to frontend)

5. **Graph highlighting**: Return the graph paths used in retrieval alongside the chat response

### Response format (SSE events):

```
event: retrieval
data: {"vector": 23, "keyword": 8, "graph": 15, "fused": 31}

event: token
data: {"content": "DOE's solid-state battery..."}

event: graph_highlight
data: {"nodes": ["sandia", "topic:solid_electrolyte"], "edges": [...]}

event: done
data: {"total_contracts": 31, "total_dollars": 847000000}
```

## 4. Recipe Synthesis Engine (Deep Research Mode)

Triggered by "how do you make..." queries or explicit Deep Research button.

### Phase 1: DECOMPOSE
- Dolphin3 generates 5-8 sub-queries attacking different facets of the question
- Facets: materials, processes, testing, specific chemistries, equipment, contractors

### Phase 2: EXPLORE (2-3 iterative rounds)
- Each sub-query runs through full hybrid retrieval
- New Topic nodes discovered via graph traversal generate NEW sub-queries
- Convergence: stop when round discovers <10% new Topics vs existing set
- All results deduplicated; multi-query frequency boosts ranking

### Phase 3: SYNTHESIZE
- Dolphin3 receives all discovered contracts and produces structured recipe
- Process ordering inferred from: temporal signals (FY dates), graph topology, LLM domain knowledge, contract description language
- Output: numbered steps with process name, description, contractors, investment, inputs/outputs, confidence level

### Progress streaming (SSE events):

```
event: phase
data: {"phase": "decompose", "sub_queries": 7}

event: round
data: {"round": 1, "contracts": 80, "topics": 12, "new_topics": 12}

event: round
data: {"round": 2, "contracts": 110, "topics": 18, "new_topics": 6}

event: converged
data: {"total_contracts": 125, "total_topics": 20, "rounds": 3}

event: token
data: {"content": "DOE's solid-state battery program involves..."}

event: recipe_step
data: {"step": 1, "name": "Electrolyte Synthesis", "who": ["Sandia", "ORNL"], "dollars": 213000000, "contracts": 8}

event: done
data: {"steps": 5, "confidence": "high", "total_dollars": 847000000}
```

**Note on SSE event types shared with `/api/chat`:** Both endpoints use `token` for streamed LLM text, `graph_highlight` for graph paths, and `done` for completion. The `done` event always uses `total_dollars` (not `total_obligation` or `total_investment`). Recipe-specific events (`phase`, `round`, `converged`, `recipe_step`) are only emitted by `/api/recipe`. The frontend `ProcessChain.svelte` component renders `recipe_step` events as a visual step sequence.

### Cost & Performance
- ~10-15 Dolphin3 calls per recipe (decompose + sub-queries + synthesis)
- ~30-60 seconds on Apple Silicon via Metal
- No API costs (all local)

## 5. Frontend Design

### Layout: Split-Pane (Chat 40% | Graph 60%)

- **Left panel (40%)**: Chat interface
  - Message history with streaming responses
  - Retrieval source badges (Vector/Keyword/Graph) with counts
  - Inline process chain visualization when discovered
  - Clickable contract list (click → highlights in graph)
  - Recipe card rendering for deep research results
  - Input bar with Send button

- **Right panel (60%)**: Knowledge graph visualization
  - Canvas-based force-directed layout (force-graph library)
  - Node types visually distinct: circles (Recipients), rounded squares (Topics), diamonds (PSC), rings (NAICS)
  - Node size proportional to total dollar obligation
  - Edge thickness proportional to weight
  - Highlighted paths for retrieval results (purple glow)
  - Dimmed nodes for non-relevant context
  - Pan/zoom, click-to-expand, hover tooltips

- **Top toolbar**: Global filters
  - Fiscal year range slider
  - Minimum dollar threshold
  - Community filter dropdown

- **Graph overlays**:
  - Legend (node type → visual)
  - Active community info panel
  - Controls (zoom-to-fit, toggle labels, hop depth)

### Key Interactions
- Ask question → graph highlights relevant paths
- Click graph node → shows contracts in left panel
- Click contract in left panel → highlights path in graph
- Deep Research mode → graph animates as new nodes discovered per round
- Filter change → both panels update simultaneously

### Tech Stack
- SvelteKit 2 (Svelte 5) with static adapter
- force-graph (Canvas-based, handles thousands of nodes)
- EventSource API for SSE consumption
- Built once, served as static files by FastAPI

## 6. API Endpoints

| Endpoint | Method | Purpose | Response |
|----------|--------|---------|----------|
| `POST /api/chat` | POST | Hybrid RAG chat | SSE stream |
| `POST /api/recipe` | POST | Recipe synthesis deep research | SSE stream |
| `GET /api/graph?entity={id}&hops={n}` | GET | Subgraph for visualization | JSON |
| `GET /api/graph/expand/{node_id}` | GET | Expand node neighborhood | JSON |
| `GET /api/search?q={query}&mode={hybrid\|vector\|keyword}` | GET | Search without chat | JSON |
| `GET /api/communities` | GET | List Leiden communities | JSON |
| `GET /api/stats` | GET | Aggregate statistics | JSON |
| `POST /api/topics/extract` | POST | Trigger topic extraction | SSE stream |

**`/api/topics/extract` request body:**
```json
{
  "batch_size": 100,       // optional, default 100. Records per Ollama call.
  "limit": null,           // optional, default null (all unprocessed). Max records to process.
  "rebuild_graph": false   // optional, default false. If true, rebuilds graph.pkl after extraction.
}
```
Incremental behavior is automatic — already-extracted `contract_transaction_unique_key` values in `topics.db` are skipped.
| `GET /api/health` | GET | Health check | JSON |

## 7. Data Ingestion Pipeline

### Existing (reused as-is)
1. `getData.sh` → downloads CSVs from USASpending.gov
2. `ingest_to_sqlite.py` → CSVs to SQLite (250K records, 18 columns)
3. `ingest_to_chroma.py` → SQLite descriptions to ChromaDB embeddings

### New (added by this project)
4. **Graph builder** (`build_graph.py`):
   - Reads SQLite, extracts unique Recipients/PSC/NAICS
   - Builds igraph with weighted edges from contract aggregations
   - Runs Leiden community detection
   - Saves pickle + metadata JSON

5. **Topic extractor** (`extract_topics.py`):
   - Reads transaction descriptions from SQLite
   - Sends batches to Dolphin3 via Ollama for topic extraction
   - Stores extracted topics in `topics.db`
   - Updates igraph with Topic nodes + edges
   - Can run incrementally (skip already-processed records)
   - Triggerable via `/api/topics/extract` endpoint

6. **FTS5 setup** (`setup_fts.py`):
   - Creates FTS5 virtual table on `transaction_description`
   - One-time migration, runs at container startup if not exists
   - **Startup sequencing**: FastAPI's `lifespan` handler runs `setup_fts.py` BEFORE accepting requests. If FTS5 population is in progress (~30 seconds for 250K rows), the `/api/health` endpoint returns `{"status": "starting", "fts5": false}` and the app returns 503 on other endpoints until ready.

### Running Ingestion Scripts

All scripts run inside the container via `docker compose exec`:

```bash
# Build/rebuild the knowledge graph from SQLite
docker compose exec app python backend/build_graph.py

# Extract topics from descriptions (incremental, skips processed)
docker compose exec app python backend/extract_topics.py --batch-size 100

# Rebuild FTS5 index (normally automatic at startup)
docker compose exec app python backend/setup_fts.py

# After running build_graph or extract_topics, restart to reload:
docker compose restart app
```

Topic extraction is also triggerable at runtime via `POST /api/topics/extract` (streams progress via SSE), but the graph is not hot-reloaded — restart required to pick up new Topic nodes.

## 8. File Structure

```
DOE_RedTeam/
├── docker-compose.yml
├── Dockerfile
├── backend/
│   ├── server.py              # FastAPI app, static file serving
│   ├── graph_engine.py        # igraph loading, traversal, Leiden
│   ├── hybrid_retriever.py    # Vector + keyword + graph fusion
│   ├── recipe_engine.py       # Multi-query agentic synthesis
│   ├── ollama_client.py       # Async Ollama HTTP client
│   ├── build_graph.py         # Graph construction script
│   ├── extract_topics.py      # LLM topic extraction script
│   ├── setup_fts.py           # FTS5 virtual table creation
│   └── requirements.txt       # Python dependencies
├── frontend/
│   ├── package.json
│   ├── svelte.config.js
│   ├── src/
│   │   ├── routes/
│   │   │   └── +page.svelte   # Main split-pane layout
│   │   ├── lib/
│   │   │   ├── components/
│   │   │   │   ├── ChatPanel.svelte
│   │   │   │   ├── GraphPanel.svelte
│   │   │   │   ├── RecipeCard.svelte
│   │   │   │   ├── RetrievalBadges.svelte
│   │   │   │   ├── ProcessChain.svelte
│   │   │   │   ├── ContractList.svelte
│   │   │   │   └── Toolbar.svelte
│   │   │   └── stores/
│   │   │       ├── chat.ts
│   │   │       ├── graph.ts
│   │   │       └── filters.ts
│   │   └── app.html
│   └── static/
├── data/                      # Mounted volume (not in image)
│   ├── doe_contracts.db
│   ├── chroma_db/
│   ├── graph.pkl
│   └── topics.db
├── datastore_gateway.py       # Existing (preserved)
├── chat_with_contracts.py     # Existing (preserved, CLI dev utility — superseded by web UI)
├── ingest_to_sqlite.py        # Existing (preserved)
└── ingest_to_chroma.py        # Existing (preserved)
```

## 9. Dependencies

### Python (backend/requirements.txt)
- fastapi, uvicorn, sse-starlette
- igraph, leidenalg
- chromadb, sentence-transformers (model: `all-MiniLM-L6-v2`, must match existing ChromaDB embeddings)
- httpx (async Ollama client)
- pandas, aiosqlite

### Node.js (frontend/package.json)
- @sveltejs/kit, @sveltejs/adapter-static
- svelte
- force-graph
- d3-force (transitive via force-graph)

### Docker
- Multi-stage: node:20-alpine (build) → python:3.12-slim (runtime)
- Final image ~2GB (sentence-transformers + PyTorch CPU ~1.5GB, chromadb ~200MB, base ~130MB, igraph+app ~100MB). Data files are volume-mounted, not in image.
