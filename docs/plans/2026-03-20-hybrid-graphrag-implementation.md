# DOE Contract GraphRAG — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a hybrid vector + keyword + graph RAG system with Svelte frontend for exploring DOE contract data and answering "how does DOE make X?" questions.

**Architecture:** Monolith FastAPI backend serving SvelteKit static build, with igraph knowledge graph, ChromaDB vector search, SQLite FTS5 keyword search, and Ollama (Dolphin3) for LLM. Dockerized with configurable Ollama target.

**Tech Stack:** Python 3.12, FastAPI, igraph + leidenalg, ChromaDB, sentence-transformers (all-MiniLM-L6-v2), httpx, SvelteKit 2 (Svelte 5), force-graph, Docker

**Design Spec:** `docs/plans/2026-03-20-hybrid-graphrag-design.md`

---

## File Map

### New files to create:
```
backend/
├── __init__.py
├── requirements.txt
├── server.py              → FastAPI app, lifespan, static serving, all routes
├── ollama_client.py       → Async httpx client for Ollama chat + embed
├── graph_engine.py        → igraph load/save, traversal, Leiden, subgraph extraction
├── build_graph.py         → CLI script: SQLite → igraph pickle
├── setup_fts.py           → CLI script: create FTS5 virtual table
├── hybrid_retriever.py    → Vector + keyword + graph fusion with RRF
├── recipe_engine.py       → Multi-query agentic synthesis loop
├── extract_topics.py      → CLI script: LLM topic extraction → topics.db
tests/
├── __init__.py
├── conftest.py            → Shared fixtures (temp SQLite, mock Ollama)
├── test_ollama_client.py
├── test_graph_engine.py
├── test_build_graph.py
├── test_setup_fts.py
├── test_hybrid_retriever.py
├── test_recipe_engine.py
├── test_extract_topics.py
├── test_server.py
frontend/
├── package.json
├── svelte.config.js
├── vite.config.ts
├── src/
│   ├── app.html
│   ├── app.css
│   ├── routes/+page.svelte
│   └── lib/
│       ├── components/
│       │   ├── ChatPanel.svelte
│       │   ├── GraphPanel.svelte
│       │   ├── RecipeCard.svelte
│       │   ├── RetrievalBadges.svelte
│       │   ├── ProcessChain.svelte
│       │   ├── ContractList.svelte
│       │   └── Toolbar.svelte
│       ├── stores/
│       │   ├── chat.ts
│       │   ├── graph.ts
│       │   └── filters.ts
│       └── api.ts
Dockerfile
docker-compose.yml
```

### Existing files (read-only reference, not modified):
```
datastore_gateway.py    → ContractDataStore class (preserved as CLI utility)
doe_contracts.db        → SQLite with 250K contracts
chroma_db/              → ChromaDB with 247K embeddings
ingest_to_sqlite.py     → CSV ingestion (preserved)
ingest_to_chroma.py     → Embedding ingestion (preserved)
```

---

## Task 1: Backend Project Scaffolding + Ollama Client

**Ground Truth:** Verify Ollama API at `POST http://localhost:11434/api/chat` accepts `{"model":"dolphin3","messages":[...],"stream":true}` and returns NDJSON. Verify `POST http://localhost:11434/api/tags` returns model list.

**Provides:** `backend/ollama_client.py` exporting `OllamaClient` class with `chat_stream(messages) -> AsyncGenerator[str]` and `generate(prompt) -> str`

**Requires:** Nothing (first task)

**Integration test:** `OllamaClient.chat_stream()` called with a test prompt returns at least one token string, and the final chunk has `done=true`.

**Files:**
- Create: `backend/__init__.py`
- Create: `backend/requirements.txt`
- Create: `backend/ollama_client.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/test_ollama_client.py`

### Steps:

- [ ] **Step 1: Create backend/requirements.txt**

```
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
sse-starlette>=2.0.0
igraph>=0.11.0
leidenalg>=0.10.0
chromadb>=1.0.0
sentence-transformers>=5.0.0
httpx>=0.27.0
pandas>=2.0.0
aiosqlite>=0.20.0
pytest>=8.0.0
pytest-asyncio>=0.24.0
```

- [ ] **Step 2: Install new dependencies**

Run: `pip install igraph leidenalg pytest-asyncio`
Expected: Successful install, `python3 -c "import igraph; import leidenalg; print('ok')"`

- [ ] **Step 3: Create test fixtures in conftest.py**

```python
# tests/conftest.py
import pytest
import sqlite3
import tempfile
import os

@pytest.fixture
def sample_db():
    """Create a small test SQLite DB with contract data."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    conn = sqlite3.connect(tmp.name)
    conn.execute("""
        CREATE TABLE contracts (
            contract_transaction_unique_key TEXT PRIMARY KEY,
            award_id_piid TEXT,
            action_date TEXT,
            action_date_fiscal_year INTEGER,
            federal_action_obligation REAL,
            total_dollars_obligated REAL,
            awarding_agency_name TEXT,
            awarding_sub_agency_name TEXT,
            recipient_name TEXT,
            recipient_city_name TEXT,
            recipient_state_name TEXT,
            primary_place_of_performance_city_name TEXT,
            primary_place_of_performance_state_name TEXT,
            transaction_description TEXT,
            product_or_service_code_description TEXT,
            naics_description TEXT,
            award_type TEXT,
            extent_competed TEXT
        )
    """)
    rows = [
        ("KEY001", "AWD001", "2024-01-15", 2024, 1000000.0, 5000000.0,
         "Department of Energy", "NNSA", "Sandia National Labs",
         "Albuquerque", "New Mexico", "Albuquerque", "New Mexico",
         "Fabrication of solid electrolyte thin films for lithium-ion battery applications",
         "R&D- PHYSICAL SCIENCES", "Research and Development in Physical Sciences",
         "DELIVERY ORDER", "FULL AND OPEN COMPETITION"),
        ("KEY002", "AWD001", "2024-03-20", 2024, 2000000.0, 5000000.0,
         "Department of Energy", "NNSA", "Sandia National Labs",
         "Albuquerque", "New Mexico", "Albuquerque", "New Mexico",
         "Characterization of garnet-type ceramic electrolytes for solid state batteries",
         "R&D- PHYSICAL SCIENCES", "Research and Development in Physical Sciences",
         "DELIVERY ORDER", "FULL AND OPEN COMPETITION"),
        ("KEY003", "AWD002", "2024-06-01", 2024, 3000000.0, 3000000.0,
         "Department of Energy", "Office of Science", "Oak Ridge National Lab",
         "Oak Ridge", "Tennessee", "Oak Ridge", "Tennessee",
         "Scale-up of dry electrode manufacturing process for advanced batteries",
         "R&D- ENERGY", "Research and Development in Biotechnology",
         "CONTRACT", "FULL AND OPEN COMPETITION"),
        ("KEY004", "AWD003", "2023-09-15", 2023, 500000.0, 500000.0,
         "Department of Energy", "Office of Science", "Pacific NW National Lab",
         "Richland", "Washington", "Richland", "Washington",
         "Nuclear reactor component testing and safety analysis",
         "NUCLEAR REACTOR COMPONENTS", "Nuclear Energy Research",
         "BPA CALL", "NOT COMPETED"),
        ("KEY005", "AWD004", "2024-02-10", 2024, 1500000.0, 1500000.0,
         "Department of Energy", "NNSA", "Lawrence Livermore National Lab",
         "Livermore", "California", "Livermore", "California",
         "Sulfide glass electrolyte synthesis for next-generation batteries",
         "R&D- PHYSICAL SCIENCES", "Research and Development in Physical Sciences",
         "DELIVERY ORDER", "FULL AND OPEN COMPETITION"),
    ]
    conn.executemany(
        "INSERT INTO contracts VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        rows
    )
    conn.commit()
    conn.close()
    yield tmp.name
    os.unlink(tmp.name)

@pytest.fixture
def ollama_base_url():
    """Return Ollama base URL from env or default."""
    return os.environ.get("OLLAMA_HOST", "http://localhost:11434")
```

- [ ] **Step 4: Write failing tests for OllamaClient**

```python
# tests/test_ollama_client.py
import pytest
import pytest_asyncio
from backend.ollama_client import OllamaClient

@pytest.mark.asyncio
async def test_chat_stream_returns_tokens(ollama_base_url):
    client = OllamaClient(base_url=ollama_base_url, model="dolphin3")
    tokens = []
    async for token in client.chat_stream([{"role": "user", "content": "Say hello in one word"}]):
        tokens.append(token)
    assert len(tokens) > 0
    full = "".join(tokens)
    assert len(full) > 0

@pytest.mark.asyncio
async def test_generate_returns_string(ollama_base_url):
    client = OllamaClient(base_url=ollama_base_url, model="dolphin3")
    result = await client.generate("Respond with only the word 'yes'")
    assert isinstance(result, str)
    assert len(result) > 0

@pytest.mark.asyncio
async def test_chat_stream_with_system_prompt(ollama_base_url):
    client = OllamaClient(base_url=ollama_base_url, model="dolphin3")
    messages = [
        {"role": "system", "content": "You only respond with numbers."},
        {"role": "user", "content": "What is 2+2?"},
    ]
    tokens = []
    async for token in client.chat_stream(messages):
        tokens.append(token)
    assert len(tokens) > 0
```

- [ ] **Step 5: Run tests to verify they fail**

Run: `cd /Users/rstarzl/Documents/GitHub/DOE_RedTeam && python3 -m pytest tests/test_ollama_client.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.ollama_client'`

- [ ] **Step 6: Implement OllamaClient**

```python
# backend/__init__.py
# Backend package for DOE GraphRAG

# backend/ollama_client.py
import json
from typing import AsyncGenerator
import httpx

class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "dolphin3"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def chat_stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        """Stream chat tokens from Ollama. Yields content strings."""
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={"model": self.model, "messages": messages, "stream": True},
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    content = data.get("message", {}).get("content", "")
                    if content:
                        yield content
                    if data.get("done"):
                        break

    async def generate(self, prompt: str) -> str:
        """Single-shot generation. Returns full response text."""
        async with httpx.AsyncClient(timeout=None) as client:
            resp = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                },
            )
            resp.raise_for_status()
            return resp.json()["message"]["content"]

    async def is_available(self) -> bool:
        """Check if Ollama is reachable and model is loaded."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                models = [m["name"] for m in resp.json().get("models", [])]
                return any(self.model in m for m in models)
        except Exception:
            return False
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd /Users/rstarzl/Documents/GitHub/DOE_RedTeam && python3 -m pytest tests/test_ollama_client.py -v`
Expected: PASS (requires Ollama running with dolphin3)

- [ ] **Step 8: Commit**

```bash
git add backend/ tests/
git commit -m "feat: add backend scaffolding and Ollama async client"
```

---

## Task 2: FTS5 Setup Script

**Ground Truth:** SQLite FTS5 is a built-in extension. Create virtual table with: `CREATE VIRTUAL TABLE contracts_fts USING fts5(contract_transaction_unique_key, transaction_description, content=contracts, content_rowid=rowid)`. Verify with `SELECT * FROM contracts_fts WHERE contracts_fts MATCH 'battery' LIMIT 5`.

**Provides:** `backend/setup_fts.py` as CLI script and importable `ensure_fts5(db_path) -> bool` function. The FTS5 table `contracts_fts` on `transaction_description`.

**Requires:** Existing `doe_contracts.db` with `contracts` table.

**Integration test:** After running `ensure_fts5()`, `SELECT * FROM contracts_fts WHERE contracts_fts MATCH 'battery'` returns rows.

**Files:**
- Create: `backend/setup_fts.py`
- Create: `tests/test_setup_fts.py`

### Steps:

- [ ] **Step 1: Write failing test**

```python
# tests/test_setup_fts.py
import sqlite3
import pytest
from backend.setup_fts import ensure_fts5, search_fts5

def test_ensure_fts5_creates_table(sample_db):
    result = ensure_fts5(sample_db)
    assert result is True
    conn = sqlite3.connect(sample_db)
    rows = conn.execute(
        "SELECT * FROM contracts_fts WHERE contracts_fts MATCH 'electrolyte'"
    ).fetchall()
    conn.close()
    assert len(rows) >= 2  # KEY001 and KEY002 mention electrolyte

def test_ensure_fts5_idempotent(sample_db):
    ensure_fts5(sample_db)
    ensure_fts5(sample_db)  # Should not raise
    conn = sqlite3.connect(sample_db)
    rows = conn.execute(
        "SELECT * FROM contracts_fts WHERE contracts_fts MATCH 'battery'"
    ).fetchall()
    conn.close()
    assert len(rows) >= 3  # KEY001, KEY002, KEY005 mention battery

def test_search_fts5_returns_keys(sample_db):
    ensure_fts5(sample_db)
    keys = search_fts5(sample_db, "nuclear reactor", limit=10)
    assert "KEY004" in keys
    assert "KEY001" not in keys  # Not about nuclear reactors
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_setup_fts.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement setup_fts.py**

```python
# backend/setup_fts.py
"""Create and populate FTS5 virtual table for keyword search."""
import sqlite3
import argparse

def ensure_fts5(db_path: str) -> bool:
    """Create FTS5 virtual table if it doesn't exist. Returns True when ready."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if FTS5 table already exists
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='contracts_fts'"
    )
    if cursor.fetchone():
        conn.close()
        return True

    # Create FTS5 virtual table
    cursor.execute("""
        CREATE VIRTUAL TABLE contracts_fts USING fts5(
            contract_transaction_unique_key,
            transaction_description,
            content=contracts,
            content_rowid=rowid
        )
    """)

    # Populate from contracts table
    cursor.execute("""
        INSERT INTO contracts_fts(rowid, contract_transaction_unique_key, transaction_description)
        SELECT rowid, contract_transaction_unique_key, transaction_description
        FROM contracts
        WHERE transaction_description IS NOT NULL
    """)

    conn.commit()
    conn.close()
    return True


def search_fts5(db_path: str, query: str, limit: int = 20) -> list[str]:
    """Search FTS5 and return matching contract_transaction_unique_keys."""
    conn = sqlite3.connect(db_path)
    # FTS5 MATCH requires special query syntax; wrap terms in quotes for phrase
    # Use simple term matching (OR by default in FTS5)
    rows = conn.execute(
        "SELECT contract_transaction_unique_key FROM contracts_fts "
        "WHERE contracts_fts MATCH ? LIMIT ?",
        (query, limit),
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Set up FTS5 for DOE contracts")
    parser.add_argument("--db", default="doe_contracts.db", help="Path to SQLite DB")
    args = parser.parse_args()
    print(f"Setting up FTS5 on {args.db}...")
    ensure_fts5(args.db)
    print("FTS5 ready.")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_setup_fts.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/setup_fts.py tests/test_setup_fts.py
git commit -m "feat: add FTS5 setup script for keyword search"
```

---

## Task 3: Graph Engine + Build Script

**Ground Truth:** Verify `igraph.Graph()` API: `g.add_vertices(n)`, `g.vs["name"] = [...]`, `g.add_edges([(0,1)])`, `g.es["weight"] = [...]`. Verify `leidenalg.find_partition(g, leidenalg.ModularityVertexPartition)` returns partition object with `.membership` list. Verify `g.write_pickle(path)` and `igraph.Graph.Read_Pickle(path)`.

**Provides:** `backend/graph_engine.py` exporting `GraphEngine` class with `load(pkl_path)`, `get_subgraph(entity_id, hops)`, `get_neighbors(node_id)`, `get_communities()`, `search_nodes(query_text)`. Also `backend/build_graph.py` CLI script that reads SQLite and produces `graph.pkl`.

**Requires:** Task 1 conftest.py fixtures (`sample_db`).

**Integration test:** `build_graph(sample_db, output_path)` produces a pickle file. `GraphEngine.load(output_path)` loads it. `engine.get_subgraph("Sandia National Labs", hops=1)` returns nodes including PSC and NAICS nodes connected to Sandia.

**Files:**
- Create: `backend/graph_engine.py`
- Create: `backend/build_graph.py`
- Create: `tests/test_graph_engine.py`
- Create: `tests/test_build_graph.py`

### Steps:

- [ ] **Step 1: Write failing test for build_graph**

```python
# tests/test_build_graph.py
import os
import tempfile
import pytest
from backend.build_graph import build_graph

def test_build_graph_creates_pickle(sample_db):
    with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
        output_path = f.name
    try:
        stats = build_graph(sample_db, output_path)
        assert os.path.exists(output_path)
        assert stats["recipient_count"] > 0
        assert stats["psc_count"] > 0
        assert stats["naics_count"] > 0
        assert stats["edge_count"] > 0
        assert stats["community_count"] > 0
    finally:
        os.unlink(output_path)

def test_build_graph_correct_nodes(sample_db):
    with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
        output_path = f.name
    try:
        stats = build_graph(sample_db, output_path)
        # sample_db has 4 unique recipients, 3 unique PSC, 3 unique NAICS
        assert stats["recipient_count"] == 4  # Sandia, ORNL, PNNL, LLNL
        assert stats["psc_count"] == 3  # R&D Physical, R&D Energy, Nuclear Reactor
        assert stats["naics_count"] == 3  # Physical Sciences, Biotech, Nuclear Energy
    finally:
        os.unlink(output_path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_build_graph.py -v`
Expected: FAIL

- [ ] **Step 3: Implement build_graph.py**

```python
# backend/build_graph.py
"""Build knowledge graph from SQLite contracts data."""
import sqlite3
import argparse
import json
import igraph as ig
import leidenalg

def build_graph(db_path: str, output_path: str, topics_db_path: str | None = None) -> dict:
    """Build igraph from contract aggregations. Returns stats dict."""
    conn = sqlite3.connect(db_path)

    # 1. Extract unique entities
    recipients = conn.execute(
        "SELECT DISTINCT recipient_name, recipient_state_name, recipient_city_name, "
        "SUM(federal_action_obligation) as total "
        "FROM contracts WHERE recipient_name IS NOT NULL "
        "GROUP BY recipient_name, recipient_state_name, recipient_city_name"
    ).fetchall()

    pscs = conn.execute(
        "SELECT DISTINCT product_or_service_code_description "
        "FROM contracts WHERE product_or_service_code_description IS NOT NULL"
    ).fetchall()

    naics = conn.execute(
        "SELECT DISTINCT naics_description "
        "FROM contracts WHERE naics_description IS NOT NULL"
    ).fetchall()

    # 2. Build node lists with type prefixes for unique IDs
    g = ig.Graph()
    node_map = {}  # name -> vertex index

    # Add recipient nodes
    for name, state, city, total in recipients:
        idx = g.vcount()
        g.add_vertices(1)
        g.vs[idx]["name"] = f"recipient:{name}"
        g.vs[idx]["label"] = name
        g.vs[idx]["type"] = "recipient"
        g.vs[idx]["state"] = state
        g.vs[idx]["city"] = city
        g.vs[idx]["total_obligated"] = total or 0
        node_map[f"recipient:{name}"] = idx

    # Add PSC nodes
    for (desc,) in pscs:
        idx = g.vcount()
        g.add_vertices(1)
        g.vs[idx]["name"] = f"psc:{desc}"
        g.vs[idx]["label"] = desc
        g.vs[idx]["type"] = "psc"
        node_map[f"psc:{desc}"] = idx

    # Add NAICS nodes
    for (desc,) in naics:
        idx = g.vcount()
        g.add_vertices(1)
        g.vs[idx]["name"] = f"naics:{desc}"
        g.vs[idx]["label"] = desc
        g.vs[idx]["type"] = "naics"
        node_map[f"naics:{desc}"] = idx

    # 3. Build edges from contract aggregations
    # Recipient <-> PSC
    r_psc = conn.execute(
        "SELECT recipient_name, product_or_service_code_description, "
        "SUM(federal_action_obligation), COUNT(*) "
        "FROM contracts "
        "WHERE recipient_name IS NOT NULL AND product_or_service_code_description IS NOT NULL "
        "GROUP BY recipient_name, product_or_service_code_description"
    ).fetchall()

    edges = []
    weights = []
    edge_types = []
    contract_counts = []

    for rname, psc_desc, total_dollars, count in r_psc:
        src = node_map.get(f"recipient:{rname}")
        tgt = node_map.get(f"psc:{psc_desc}")
        if src is not None and tgt is not None:
            edges.append((src, tgt))
            weights.append(abs(total_dollars or 0))
            edge_types.append("recipient_psc")
            contract_counts.append(count)

    # Recipient <-> NAICS
    r_naics = conn.execute(
        "SELECT recipient_name, naics_description, "
        "SUM(federal_action_obligation), COUNT(*) "
        "FROM contracts "
        "WHERE recipient_name IS NOT NULL AND naics_description IS NOT NULL "
        "GROUP BY recipient_name, naics_description"
    ).fetchall()

    for rname, naics_desc, total_dollars, count in r_naics:
        src = node_map.get(f"recipient:{rname}")
        tgt = node_map.get(f"naics:{naics_desc}")
        if src is not None and tgt is not None:
            edges.append((src, tgt))
            weights.append(abs(total_dollars or 0))
            edge_types.append("recipient_naics")
            contract_counts.append(count)

    # PSC <-> NAICS co-occurrence
    psc_naics = conn.execute(
        "SELECT product_or_service_code_description, naics_description, COUNT(*) "
        "FROM contracts "
        "WHERE product_or_service_code_description IS NOT NULL "
        "AND naics_description IS NOT NULL "
        "GROUP BY product_or_service_code_description, naics_description"
    ).fetchall()

    for psc_desc, naics_desc, count in psc_naics:
        src = node_map.get(f"psc:{psc_desc}")
        tgt = node_map.get(f"naics:{naics_desc}")
        if src is not None and tgt is not None:
            edges.append((src, tgt))
            weights.append(count)
            edge_types.append("psc_naics")
            contract_counts.append(count)

    conn.close()

    # 4. Add all edges
    g.add_edges(edges)
    g.es["weight"] = weights
    g.es["edge_type"] = edge_types
    g.es["contract_count"] = contract_counts

    # 5. Community detection
    partition = leidenalg.find_partition(
        g, leidenalg.ModularityVertexPartition,
        weights=g.es["weight"] if g.ecount() > 0 else None
    )
    g.vs["community"] = partition.membership

    # 6. Save
    g.write_pickle(output_path)

    # 7. Save metadata
    meta = {
        "recipient_count": sum(1 for v in g.vs if v["type"] == "recipient"),
        "psc_count": sum(1 for v in g.vs if v["type"] == "psc"),
        "naics_count": sum(1 for v in g.vs if v["type"] == "naics"),
        "edge_count": g.ecount(),
        "community_count": max(partition.membership) + 1 if partition.membership else 0,
    }
    meta_path = output_path.replace(".pkl", "_meta.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    return meta


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build knowledge graph from DOE contracts")
    parser.add_argument("--db", default="doe_contracts.db")
    parser.add_argument("--output", default="graph.pkl")
    parser.add_argument("--topics-db", default=None)
    args = parser.parse_args()
    print(f"Building graph from {args.db}...")
    stats = build_graph(args.db, args.output, args.topics_db)
    print(f"Graph built: {stats}")
```

- [ ] **Step 4: Run build_graph tests**

Run: `python3 -m pytest tests/test_build_graph.py -v`
Expected: PASS

- [ ] **Step 5: Write failing test for GraphEngine**

```python
# tests/test_graph_engine.py
import tempfile
import os
import pytest
from backend.build_graph import build_graph
from backend.graph_engine import GraphEngine

@pytest.fixture
def graph_engine(sample_db):
    with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
        pkl_path = f.name
    build_graph(sample_db, pkl_path)
    engine = GraphEngine(pkl_path)
    yield engine
    os.unlink(pkl_path)
    meta_path = pkl_path.replace(".pkl", "_meta.json")
    if os.path.exists(meta_path):
        os.unlink(meta_path)

def test_load_graph(graph_engine):
    assert graph_engine.node_count > 0
    assert graph_engine.edge_count > 0

def test_get_subgraph(graph_engine):
    subgraph = graph_engine.get_subgraph("recipient:Sandia National Labs", hops=1)
    assert len(subgraph["nodes"]) > 1  # Sandia + connected nodes
    assert len(subgraph["edges"]) > 0
    node_names = [n["name"] for n in subgraph["nodes"]]
    assert "recipient:Sandia National Labs" in node_names

def test_search_nodes(graph_engine):
    results = graph_engine.search_nodes("Sandia")
    assert len(results) > 0
    assert any("Sandia" in r["label"] for r in results)

def test_get_communities(graph_engine):
    communities = graph_engine.get_communities()
    assert len(communities) > 0
    assert all("id" in c and "node_count" in c for c in communities)

def test_get_neighbors(graph_engine):
    neighbors = graph_engine.get_neighbors("recipient:Sandia National Labs")
    assert len(neighbors) > 0
    # Should include PSC and NAICS nodes connected to Sandia
    types = {n["type"] for n in neighbors}
    assert "psc" in types or "naics" in types
```

- [ ] **Step 6: Implement GraphEngine**

```python
# backend/graph_engine.py
"""Runtime graph engine: load, traverse, query the knowledge graph."""
import igraph as ig

class GraphEngine:
    def __init__(self, pkl_path: str):
        self.graph = ig.Graph.Read_Pickle(pkl_path)
        self._name_index: dict[str, int] = {
            v["name"]: v.index for v in self.graph.vs
        }

    @property
    def node_count(self) -> int:
        return self.graph.vcount()

    @property
    def edge_count(self) -> int:
        return self.graph.ecount()

    def _vertex_to_dict(self, v) -> dict:
        return {
            "id": v.index,
            "name": v["name"],
            "label": v["label"],
            "type": v["type"],
            "community": v["community"],
            **{k: v[k] for k in v.attributes() if k not in ("name", "label", "type", "community")},
        }

    def _edge_to_dict(self, e) -> dict:
        return {
            "source": self.graph.vs[e.source]["name"],
            "target": self.graph.vs[e.target]["name"],
            "weight": e["weight"],
            "edge_type": e["edge_type"],
            "contract_count": e["contract_count"],
        }

    def get_subgraph(self, entity_name: str, hops: int = 1) -> dict:
        """Get subgraph around an entity within N hops."""
        idx = self._name_index.get(entity_name)
        if idx is None:
            return {"nodes": [], "edges": []}

        # BFS to collect vertices within hops
        visited = {idx}
        frontier = {idx}
        for _ in range(hops):
            next_frontier = set()
            for v in frontier:
                for neighbor in self.graph.neighbors(v):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        next_frontier.add(neighbor)
            frontier = next_frontier

        # Extract subgraph
        nodes = [self._vertex_to_dict(self.graph.vs[v]) for v in visited]
        edges = [
            self._edge_to_dict(e)
            for e in self.graph.es
            if e.source in visited and e.target in visited
        ]
        return {"nodes": nodes, "edges": edges}

    def get_neighbors(self, entity_name: str) -> list[dict]:
        """Get immediate neighbors of an entity."""
        idx = self._name_index.get(entity_name)
        if idx is None:
            return []
        return [self._vertex_to_dict(self.graph.vs[n]) for n in self.graph.neighbors(idx)]

    def search_nodes(self, query: str, limit: int = 20) -> list[dict]:
        """Search nodes by label substring match."""
        query_lower = query.lower()
        results = []
        for v in self.graph.vs:
            if query_lower in (v["label"] or "").lower():
                results.append(self._vertex_to_dict(v))
                if len(results) >= limit:
                    break
        return results

    def get_communities(self) -> list[dict]:
        """Return community summaries."""
        communities: dict[int, list] = {}
        for v in self.graph.vs:
            cid = v["community"]
            communities.setdefault(cid, []).append(v)

        result = []
        for cid, members in communities.items():
            types = {}
            for m in members:
                types.setdefault(m["type"], []).append(m["label"])
            total = sum(
                m.get("total_obligated", 0) or 0
                for m in members if m["type"] == "recipient"
            )
            result.append({
                "id": cid,
                "node_count": len(members),
                "types": {t: len(names) for t, names in types.items()},
                "top_recipients": sorted(
                    [m["label"] for m in members if m["type"] == "recipient"],
                    key=lambda x: x
                )[:5],
                "total_obligated": total,
            })
        return sorted(result, key=lambda c: c["total_obligated"], reverse=True)

    def get_graph_paths(self, node_names: list[str]) -> dict:
        """Given a set of node names, return the subgraph connecting them."""
        indices = [self._name_index[n] for n in node_names if n in self._name_index]
        if len(indices) < 2:
            return {"nodes": [], "edges": []}

        # Collect all edges between the given nodes and their shared neighbors
        visited = set(indices)
        edges = []
        for e in self.graph.es:
            if e.source in visited and e.target in visited:
                edges.append(self._edge_to_dict(e))

        nodes = [self._vertex_to_dict(self.graph.vs[v]) for v in visited]
        return {"nodes": nodes, "edges": edges}
```

- [ ] **Step 7: Run graph engine tests**

Run: `python3 -m pytest tests/test_graph_engine.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add backend/build_graph.py backend/graph_engine.py tests/test_build_graph.py tests/test_graph_engine.py
git commit -m "feat: add knowledge graph builder and runtime engine"
```

---

## Task 4: Hybrid Retriever

**Ground Truth:** Verify ChromaDB `collection.query(query_embeddings=[...], n_results=20)` returns `{"ids": [[...]], "distances": [[...]]}`. Verify `SentenceTransformer('all-MiniLM-L6-v2').encode("test")` returns 384-dim numpy array. Verify RRF formula: `score = Σ 1/(k + rank)` with k=60.

**Provides:** `backend/hybrid_retriever.py` exporting `HybridRetriever` class with `search(query, n_results) -> HybridResults` containing ranked contracts with source tags and graph paths.

**Requires:** Task 2 (`setup_fts.py` for keyword search), Task 3 (`GraphEngine` for graph traversal), existing ChromaDB collection.

**Integration test:** `retriever.search("solid state battery")` returns results with at least 2 sources (vector + keyword) and each result has a `sources` list.

**Files:**
- Create: `backend/hybrid_retriever.py`
- Create: `tests/test_hybrid_retriever.py`

### Steps:

- [ ] **Step 1: Write failing test**

```python
# tests/test_hybrid_retriever.py
import tempfile
import os
import pytest
from backend.build_graph import build_graph
from backend.graph_engine import GraphEngine
from backend.setup_fts import ensure_fts5
from backend.hybrid_retriever import HybridRetriever

@pytest.fixture
def retriever(sample_db):
    """Create retriever with sample DB (no ChromaDB — vector search will return empty)."""
    ensure_fts5(sample_db)
    with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
        pkl_path = f.name
    build_graph(sample_db, pkl_path)
    engine = GraphEngine(pkl_path)
    retriever = HybridRetriever(
        db_path=sample_db,
        graph_engine=engine,
        chroma_path=None,  # Skip vector search in unit tests
    )
    yield retriever
    os.unlink(pkl_path)

def test_keyword_search(retriever):
    results = retriever.search_keyword("electrolyte", limit=10)
    assert len(results) > 0
    assert all("contract_transaction_unique_key" in r for r in results)

def test_graph_search(retriever):
    results = retriever.search_graph("battery", hops=1)
    assert isinstance(results, dict)
    assert "contracts" in results
    assert "paths" in results

def test_hybrid_search(retriever):
    results = retriever.search("electrolyte", n_results=10)
    assert len(results.contracts) > 0
    assert all(hasattr(c, "sources") for c in results.contracts)
    assert results.retrieval_counts["keyword"] > 0

def test_rrf_fusion(retriever):
    """Test that RRF properly ranks contracts found by multiple sources higher."""
    results = retriever.search("solid electrolyte", n_results=10)
    # KEY001 and KEY002 should rank high (match keyword "electrolyte")
    keys = [c.key for c in results.contracts]
    assert "KEY001" in keys or "KEY002" in keys
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_hybrid_retriever.py -v`
Expected: FAIL

- [ ] **Step 3: Implement HybridRetriever**

```python
# backend/hybrid_retriever.py
"""Hybrid retrieval: vector + keyword + graph, fused with RRF."""
import sqlite3
from dataclasses import dataclass, field
from backend.setup_fts import search_fts5
from backend.graph_engine import GraphEngine

try:
    import chromadb
    from sentence_transformers import SentenceTransformer
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False


@dataclass
class ContractResult:
    key: str
    description: str
    recipient: str
    obligation: float
    fiscal_year: int
    psc: str
    naics: str
    sources: list[str] = field(default_factory=list)
    rrf_score: float = 0.0


@dataclass
class HybridResults:
    contracts: list[ContractResult]
    retrieval_counts: dict[str, int]
    graph_paths: dict


RRF_K = 60


class HybridRetriever:
    def __init__(
        self,
        db_path: str,
        graph_engine: GraphEngine | None = None,
        chroma_path: str | None = None,
    ):
        self.db_path = db_path
        self.graph_engine = graph_engine
        self.chroma_collection = None
        self.embed_model = None

        if chroma_path and CHROMA_AVAILABLE:
            client = chromadb.PersistentClient(path=chroma_path)
            try:
                self.chroma_collection = client.get_collection("doe_contracts")
                self.embed_model = SentenceTransformer("all-MiniLM-L6-v2")
            except Exception:
                pass

    def _get_contracts_by_keys(self, keys: list[str]) -> dict[str, dict]:
        """Fetch full contract records from SQLite by keys."""
        if not keys:
            return {}
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        placeholders = ",".join("?" * len(keys))
        rows = conn.execute(
            f"SELECT * FROM contracts WHERE contract_transaction_unique_key IN ({placeholders})",
            keys,
        ).fetchall()
        conn.close()
        return {row["contract_transaction_unique_key"]: dict(row) for row in rows}

    def search_vector(self, query: str, limit: int = 20) -> list[str]:
        """Semantic search via ChromaDB. Returns ranked contract keys."""
        if not self.chroma_collection or not self.embed_model:
            return []
        embedding = self.embed_model.encode(query).tolist()
        results = self.chroma_collection.query(
            query_embeddings=[embedding], n_results=limit
        )
        return results["ids"][0] if results["ids"] else []

    def search_keyword(self, query: str, limit: int = 20) -> list[dict]:
        """FTS5 keyword search. Returns contract dicts."""
        keys = search_fts5(self.db_path, query, limit=limit)
        contracts = self._get_contracts_by_keys(keys)
        return [contracts[k] for k in keys if k in contracts]

    def search_graph(self, query: str, hops: int = 1) -> dict:
        """Graph-based search: find matching nodes, traverse, return connected contracts."""
        if not self.graph_engine:
            return {"contracts": [], "paths": {"nodes": [], "edges": []}}

        # Find matching graph nodes
        matching_nodes = self.graph_engine.search_nodes(query, limit=10)
        if not matching_nodes:
            return {"contracts": [], "paths": {"nodes": [], "edges": []}}

        # Gather contract keys from neighbors of matching nodes
        all_contract_keys = set()
        all_node_names = set()

        for node in matching_nodes:
            all_node_names.add(node["name"])
            subgraph = self.graph_engine.get_subgraph(node["name"], hops=hops)
            all_node_names.update(n["name"] for n in subgraph["nodes"])

            # Get recipient names from the subgraph
            recipient_names = [
                n["label"] for n in subgraph["nodes"] if n["type"] == "recipient"
            ]
            if recipient_names:
                conn = sqlite3.connect(self.db_path)
                placeholders = ",".join("?" * len(recipient_names))
                rows = conn.execute(
                    f"SELECT contract_transaction_unique_key FROM contracts "
                    f"WHERE recipient_name IN ({placeholders}) LIMIT 50",
                    recipient_names,
                ).fetchall()
                conn.close()
                all_contract_keys.update(r[0] for r in rows)

        # Get graph paths for visualization
        paths = self.graph_engine.get_graph_paths(list(all_node_names))

        return {"contracts": list(all_contract_keys), "paths": paths}

    def search(self, query: str, n_results: int = 15) -> HybridResults:
        """Full hybrid search with RRF fusion."""
        # 1. Parallel retrieval (sequential in sync code, async in server)
        vector_keys = self.search_vector(query, limit=20)
        keyword_results = self.search_keyword(query, limit=20)
        keyword_keys = [r["contract_transaction_unique_key"] for r in keyword_results]
        graph_result = self.search_graph(query, hops=1)
        graph_keys = graph_result["contracts"]

        # 2. Build ranked lists for RRF
        rankings = {}  # key -> {source: rank}
        for rank, key in enumerate(vector_keys):
            rankings.setdefault(key, {})["vector"] = rank + 1
        for rank, key in enumerate(keyword_keys):
            rankings.setdefault(key, {})["keyword"] = rank + 1
        for rank, key in enumerate(graph_keys):
            rankings.setdefault(key, {})["graph"] = rank + 1

        # 3. Compute RRF scores
        scored = []
        for key, sources in rankings.items():
            score = sum(1.0 / (RRF_K + rank) for rank in sources.values())
            scored.append((key, score, list(sources.keys())))
        scored.sort(key=lambda x: x[1], reverse=True)

        # 4. Fetch full records for top N
        top_keys = [s[0] for s in scored[:n_results]]
        contracts_data = self._get_contracts_by_keys(top_keys)

        # 5. Build results
        contracts = []
        for key, score, sources in scored[:n_results]:
            data = contracts_data.get(key, {})
            if not data:
                continue
            contracts.append(ContractResult(
                key=key,
                description=data.get("transaction_description", ""),
                recipient=data.get("recipient_name", ""),
                obligation=data.get("federal_action_obligation", 0) or 0,
                fiscal_year=data.get("action_date_fiscal_year", 0) or 0,
                psc=data.get("product_or_service_code_description", ""),
                naics=data.get("naics_description", ""),
                sources=sources,
                rrf_score=score,
            ))

        return HybridResults(
            contracts=contracts,
            retrieval_counts={
                "vector": len(vector_keys),
                "keyword": len(keyword_keys),
                "graph": len(graph_keys),
                "fused": len(scored),
            },
            graph_paths=graph_result.get("paths", {"nodes": [], "edges": []}),
        )
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_hybrid_retriever.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/hybrid_retriever.py tests/test_hybrid_retriever.py
git commit -m "feat: add hybrid retriever with RRF fusion"
```

---

## Task 5: Recipe Synthesis Engine

**Ground Truth:** Verify Ollama `/api/chat` with `stream: false` returns `{"message": {"content": "..."}}`. The recipe engine calls `OllamaClient.generate()` for decomposition and synthesis, `HybridRetriever.search()` for each sub-query.

**Provides:** `backend/recipe_engine.py` exporting `RecipeEngine` class with `async synthesize(query) -> AsyncGenerator[dict]` yielding SSE-compatible event dicts (phase, round, converged, token, recipe_step, done).

**Requires:** Task 1 (`OllamaClient`), Task 4 (`HybridRetriever`).

**Integration test:** `recipe_engine.synthesize("How do you make batteries?")` yields at least one `phase` event, at least one `round` event, and a `done` event.

**Files:**
- Create: `backend/recipe_engine.py`
- Create: `tests/test_recipe_engine.py`

### Steps:

- [ ] **Step 1: Write failing test**

```python
# tests/test_recipe_engine.py
import pytest
import tempfile
import os
from unittest.mock import AsyncMock, patch
from backend.recipe_engine import RecipeEngine

@pytest.fixture
def mock_retriever():
    """Mock retriever that returns canned results."""
    from backend.hybrid_retriever import HybridResults, ContractResult
    mock = AsyncMock()
    mock.search.return_value = HybridResults(
        contracts=[
            ContractResult(
                key="KEY001", description="Solid electrolyte fabrication",
                recipient="Sandia", obligation=1000000, fiscal_year=2024,
                psc="R&D", naics="Physical Sciences", sources=["keyword"],
            ),
        ],
        retrieval_counts={"vector": 0, "keyword": 1, "graph": 0},
        graph_paths={"nodes": [], "edges": []},
    )
    return mock

@pytest.fixture
def mock_ollama():
    """Mock Ollama client."""
    mock = AsyncMock()
    mock.generate.return_value = '["solid electrolyte fabrication", "electrode manufacturing"]'
    return mock

@pytest.mark.asyncio
async def test_decompose_generates_sub_queries(mock_ollama, mock_retriever):
    engine = RecipeEngine(ollama=mock_ollama, retriever=mock_retriever)
    events = []
    async for event in engine.synthesize("How do you make batteries?"):
        events.append(event)
    phase_events = [e for e in events if e["event"] == "phase"]
    assert len(phase_events) >= 1
    assert phase_events[0]["data"]["phase"] == "decompose"

@pytest.mark.asyncio
async def test_synthesize_emits_done(mock_ollama, mock_retriever):
    engine = RecipeEngine(ollama=mock_ollama, retriever=mock_retriever)
    events = []
    async for event in engine.synthesize("How do you make batteries?"):
        events.append(event)
    done_events = [e for e in events if e["event"] == "done"]
    assert len(done_events) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_recipe_engine.py -v`
Expected: FAIL

- [ ] **Step 3: Implement RecipeEngine**

```python
# backend/recipe_engine.py
"""Recipe synthesis engine: multi-query agentic research loop."""
import asyncio
import json
from typing import AsyncGenerator
from backend.ollama_client import OllamaClient
from backend.hybrid_retriever import HybridRetriever, ContractResult

DECOMPOSE_PROMPT = """You are a research assistant analyzing DOE contract data.
Given this question: "{query}"

Generate 5-8 specific search queries to find ALL relevant contracts.
Attack different facets: materials, processes, testing, chemistries, equipment, contractors.
Return ONLY a JSON array of strings. No explanation.

Example: ["solid electrolyte thin film fabrication", "lithium cathode manufacturing", ...]"""

SYNTHESIZE_PROMPT = """You are a DOE process intelligence analyst.
Based on the following contract evidence, synthesize a manufacturing recipe.

QUESTION: {query}

CONTRACTS FOUND ({count} total, ${dollars:,.0f} invested):
{evidence}

Create a step-by-step manufacturing process. For each step provide:
1. Step name
2. Brief description of the process
3. Which contractors/labs do this work
4. Approximate investment

Format as numbered steps. Be specific about processes, materials, and techniques.
Base your answer ONLY on the contract evidence above."""


class RecipeEngine:
    def __init__(
        self,
        ollama: OllamaClient,
        retriever: HybridRetriever,
        max_rounds: int = 3,
    ):
        self.ollama = ollama
        self.retriever = retriever
        self.max_rounds = max_rounds

    async def synthesize(self, query: str) -> AsyncGenerator[dict, None]:
        """Run the full recipe synthesis loop. Yields SSE-compatible event dicts."""

        # Phase 1: DECOMPOSE
        decompose_prompt = DECOMPOSE_PROMPT.format(query=query)
        raw_response = await self.ollama.generate(decompose_prompt)

        try:
            # Try to parse JSON array from response
            sub_queries = json.loads(raw_response)
            if not isinstance(sub_queries, list):
                sub_queries = [query]
        except json.JSONDecodeError:
            sub_queries = [query]

        # Ensure we always include the original query
        if query not in sub_queries:
            sub_queries.insert(0, query)

        yield {"event": "phase", "data": {"phase": "decompose", "sub_queries": len(sub_queries)}}

        # Phase 2: EXPLORE
        all_contracts: dict[str, ContractResult] = {}
        all_topics: set[str] = set()
        all_graph_paths = {"nodes": [], "edges": []}

        for round_num in range(1, self.max_rounds + 1):
            round_new_topics = set()

            for sq in sub_queries:
                # Run sync retriever in thread to avoid blocking event loop
                results = await asyncio.to_thread(self.retriever.search, sq, 20)
                for contract in results.contracts:
                    if contract.key not in all_contracts:
                        all_contracts[contract.key] = contract
                # Collect topics from graph paths
                for node in results.graph_paths.get("nodes", []):
                    if node.get("type") == "topic":
                        topic_name = node.get("label", "")
                        if topic_name and topic_name not in all_topics:
                            round_new_topics.add(topic_name)
                            all_topics.add(topic_name)

                # Merge graph paths
                all_graph_paths["nodes"].extend(results.graph_paths.get("nodes", []))
                all_graph_paths["edges"].extend(results.graph_paths.get("edges", []))

            yield {
                "event": "round",
                "data": {
                    "round": round_num,
                    "contracts": len(all_contracts),
                    "topics": len(all_topics),
                    "new_topics": len(round_new_topics),
                },
            }

            # Convergence check: <10% new topics
            if len(all_topics) > 0 and len(round_new_topics) / max(len(all_topics), 1) < 0.1:
                break

            # Generate new sub-queries from discovered topics for next round
            if round_new_topics:
                sub_queries = list(round_new_topics)[:5]
            else:
                break

        yield {
            "event": "converged",
            "data": {
                "total_contracts": len(all_contracts),
                "total_topics": len(all_topics),
                "rounds": round_num,
            },
        }

        # Phase 3: SYNTHESIZE
        total_dollars = sum(c.obligation for c in all_contracts.values())
        evidence_lines = []
        for c in sorted(all_contracts.values(), key=lambda x: abs(x.obligation), reverse=True)[:30]:
            evidence_lines.append(
                f"- {c.recipient}: {c.description} (${c.obligation:,.0f}, FY{c.fiscal_year}) [{c.psc}]"
            )

        synth_prompt = SYNTHESIZE_PROMPT.format(
            query=query,
            count=len(all_contracts),
            dollars=total_dollars,
            evidence="\n".join(evidence_lines),
        )

        # Stream the synthesis narrative
        full_response = ""
        async for token in self.ollama.chat_stream(
            [{"role": "user", "content": synth_prompt}]
        ):
            full_response += token
            yield {"event": "token", "data": {"content": token}}

        # Extract structured recipe steps from the response
        steps = self._parse_recipe_steps(full_response, all_contracts)
        for step in steps:
            yield {"event": "recipe_step", "data": step}

        # Emit graph highlight
        yield {
            "event": "graph_highlight",
            "data": all_graph_paths,
        }

        # Determine confidence based on evidence density
        confidence = "high" if len(all_contracts) > 20 else "medium" if len(all_contracts) > 5 else "low"

        yield {
            "event": "done",
            "data": {
                "steps": len(steps),
                "confidence": confidence,
                "total_contracts": len(all_contracts),
                "total_dollars": total_dollars,
            },
        }

    @staticmethod
    def _parse_recipe_steps(text: str, contracts: dict[str, ContractResult]) -> list[dict]:
        """Parse numbered steps from LLM response into structured recipe_step dicts."""
        import re
        steps = []
        # Match patterns like "1. Step Name" or "Step 1: Name"
        pattern = r'(?:^|\n)\s*(?:Step\s+)?(\d+)[.:)\-]\s*\*?\*?([^\n*]+)'
        matches = re.findall(pattern, text)
        for num, name in matches:
            # Find contractors mentioned in this step's text
            step_contractors = set()
            for c in contracts.values():
                if c.recipient and c.recipient.lower() in text.lower():
                    step_contractors.add(c.recipient)
            steps.append({
                "step": int(num),
                "name": name.strip().rstrip("*"),
                "who": list(step_contractors)[:5],
                "dollars": 0,  # Approximation — full attribution requires deeper analysis
                "contracts": 0,
            })
        return steps if steps else [{"step": 1, "name": "See narrative above", "who": [], "dollars": 0, "contracts": 0}]
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_recipe_engine.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/recipe_engine.py tests/test_recipe_engine.py
git commit -m "feat: add recipe synthesis engine with multi-query loop"
```

---

## Task 6: FastAPI Server

**Ground Truth:** Verify `fastapi.FastAPI()` with `lifespan` context manager. Verify `sse_starlette.sse.EventSourceResponse` accepts an async generator. Verify `fastapi.staticfiles.StaticFiles` serves a directory. Verify `fastapi.testclient.TestClient` can test routes.

**Provides:** `backend/server.py` — complete FastAPI app with all endpoints from the design spec. Exports `app` for uvicorn and `create_app(config)` for testing.

**Requires:** Tasks 1-5 (all backend modules).

**Integration test:** `TestClient(app).get("/api/health")` returns 200 with status. `TestClient(app).get("/api/graph?entity=recipient:Sandia&hops=1")` returns JSON with nodes and edges.

**Files:**
- Create: `backend/server.py`
- Create: `tests/test_server.py`

### Steps:

- [ ] **Step 1: Write failing test**

```python
# tests/test_server.py
import tempfile
import os
import pytest
from fastapi.testclient import TestClient
from backend.build_graph import build_graph
from backend.setup_fts import ensure_fts5

@pytest.fixture
def app_client(sample_db):
    """Create test FastAPI app with sample data."""
    ensure_fts5(sample_db)
    with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
        pkl_path = f.name
    build_graph(sample_db, pkl_path)

    os.environ["DB_PATH"] = sample_db
    os.environ["GRAPH_PATH"] = pkl_path
    os.environ["CHROMA_PATH"] = ""  # Skip in tests
    os.environ["STATIC_DIR"] = ""  # Skip in tests

    from backend.server import create_app
    app = create_app()
    client = TestClient(app)
    yield client

    os.unlink(pkl_path)
    meta_path = pkl_path.replace(".pkl", "_meta.json")
    if os.path.exists(meta_path):
        os.unlink(meta_path)

def test_health(app_client):
    resp = app_client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ready", "starting")

def test_graph_endpoint(app_client):
    resp = app_client.get("/api/graph?entity=recipient:Sandia National Labs&hops=1")
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) > 0

def test_search_endpoint(app_client):
    resp = app_client.get("/api/search?q=electrolyte&mode=keyword")
    assert resp.status_code == 200
    data = resp.json()
    assert "contracts" in data

def test_communities_endpoint(app_client):
    resp = app_client.get("/api/communities")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)

def test_stats_endpoint(app_client):
    resp = app_client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "node_count" in data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_server.py -v`
Expected: FAIL

- [ ] **Step 3: Implement server.py**

```python
# backend/server.py
"""FastAPI server for DOE GraphRAG."""
import os
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel

from backend.graph_engine import GraphEngine
from backend.hybrid_retriever import HybridRetriever
from backend.ollama_client import OllamaClient
from backend.recipe_engine import RecipeEngine
from backend.setup_fts import ensure_fts5

# Config from environment
DB_PATH = os.environ.get("DB_PATH", "doe_contracts.db")
GRAPH_PATH = os.environ.get("GRAPH_PATH", "graph.pkl")
CHROMA_PATH = os.environ.get("CHROMA_PATH", "./chroma_db")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "dolphin3")
STATIC_DIR = os.environ.get("STATIC_DIR", "frontend/build")

# Shared state
state = {}


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        if DB_PATH and os.path.exists(DB_PATH):
            ensure_fts5(DB_PATH)

        if GRAPH_PATH and os.path.exists(GRAPH_PATH):
            state["graph"] = GraphEngine(GRAPH_PATH)
        else:
            state["graph"] = None

        state["ollama"] = OllamaClient(base_url=OLLAMA_HOST, model=OLLAMA_MODEL)

        chroma = CHROMA_PATH if CHROMA_PATH and os.path.exists(CHROMA_PATH) else None
        state["retriever"] = HybridRetriever(
            db_path=DB_PATH,
            graph_engine=state["graph"],
            chroma_path=chroma,
        )

        state["recipe"] = RecipeEngine(
            ollama=state["ollama"],
            retriever=state["retriever"],
        )

        state["ready"] = True
        yield
        state.clear()

    app = FastAPI(title="DOE GraphRAG", lifespan=lifespan)

    # --- Health ---
    @app.get("/api/health")
    async def health():
        ollama_ok = await state["ollama"].is_available() if state.get("ollama") else False
        return {
            "status": "ready" if state.get("ready") else "starting",
            "graph_loaded": state.get("graph") is not None,
            "ollama_available": ollama_ok,
            "fts5": True,
        }

    # --- Graph ---
    @app.get("/api/graph")
    async def get_graph(entity: str = Query(...), hops: int = Query(1, ge=1, le=3)):
        if not state.get("graph"):
            return JSONResponse({"error": "Graph not loaded"}, 503)
        return state["graph"].get_subgraph(entity, hops=hops)

    @app.get("/api/graph/expand/{node_id}")
    async def expand_node(node_id: str):
        if not state.get("graph"):
            return JSONResponse({"error": "Graph not loaded"}, 503)
        neighbors = state["graph"].get_neighbors(node_id)
        return {"neighbors": neighbors}

    # --- Search ---
    @app.get("/api/search")
    async def search(q: str = Query(...), mode: str = Query("hybrid")):
        retriever = state["retriever"]
        if mode == "keyword":
            results = retriever.search_keyword(q)
            return {"contracts": results, "mode": mode}
        elif mode == "vector":
            keys = retriever.search_vector(q)
            contracts = retriever._get_contracts_by_keys(keys)
            return {"contracts": list(contracts.values()), "mode": mode}
        else:
            hybrid = retriever.search(q)
            return {
                "contracts": [
                    {
                        "key": c.key, "description": c.description,
                        "recipient": c.recipient, "obligation": c.obligation,
                        "fiscal_year": c.fiscal_year, "psc": c.psc,
                        "naics": c.naics, "sources": c.sources,
                        "rrf_score": c.rrf_score,
                    }
                    for c in hybrid.contracts
                ],
                "retrieval_counts": hybrid.retrieval_counts,
                "graph_paths": hybrid.graph_paths,
                "mode": mode,
            }

    # --- Communities ---
    @app.get("/api/communities")
    async def get_communities():
        if not state.get("graph"):
            return JSONResponse({"error": "Graph not loaded"}, 503)
        return state["graph"].get_communities()

    # --- Stats ---
    @app.get("/api/stats")
    async def get_stats():
        graph = state.get("graph")
        return {
            "node_count": graph.node_count if graph else 0,
            "edge_count": graph.edge_count if graph else 0,
            "communities": len(graph.get_communities()) if graph else 0,
        }

    # --- Chat (SSE) ---
    class ChatRequest(BaseModel):
        messages: list[dict]

    @app.post("/api/chat")
    async def chat(req: ChatRequest):
        retriever = state["retriever"]
        ollama = state["ollama"]

        # Extract last user message for retrieval
        user_msg = next(
            (m["content"] for m in reversed(req.messages) if m["role"] == "user"), ""
        )

        async def event_stream():
            # 1. Hybrid retrieval
            results = retriever.search(user_msg)
            yield {
                "event": "retrieval",
                "data": json.dumps(results.retrieval_counts),
            }

            # 2. Build augmented prompt
            context_lines = []
            for c in results.contracts:
                context_lines.append(
                    f"- {c.recipient}: {c.description} (${c.obligation:,.0f}, FY{c.fiscal_year})"
                )

            augmented = [
                {"role": "system", "content": "You are a DOE contract analyst. Use the provided context to answer accurately."},
                {"role": "user", "content": f"### CONTRACT RECORDS:\n" + "\n".join(context_lines) + f"\n\n### QUESTION:\n{user_msg}"},
            ]

            # 3. Stream LLM response
            async for token in ollama.chat_stream(augmented):
                yield {"event": "token", "data": json.dumps({"content": token})}

            # 4. Graph highlight
            yield {
                "event": "graph_highlight",
                "data": json.dumps(results.graph_paths),
            }

            # 5. Done
            total_dollars = sum(c.obligation for c in results.contracts)
            yield {
                "event": "done",
                "data": json.dumps({
                    "total_contracts": len(results.contracts),
                    "total_dollars": total_dollars,
                }),
            }

        return EventSourceResponse(event_stream())

    # --- Recipe (SSE) ---
    class RecipeRequest(BaseModel):
        query: str

    @app.post("/api/recipe")
    async def recipe(req: RecipeRequest):
        engine = state["recipe"]

        async def event_stream():
            async for event in engine.synthesize(req.query):
                yield {
                    "event": event["event"],
                    "data": json.dumps(event["data"]),
                }

        return EventSourceResponse(event_stream())

    # --- Static files (SvelteKit build) ---
    if STATIC_DIR and os.path.isdir(STATIC_DIR):
        app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

    return app


# For uvicorn: `uvicorn backend.server:app`
app = create_app()
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_server.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/server.py tests/test_server.py
git commit -m "feat: add FastAPI server with all API endpoints"
```

---

## Task 7: SvelteKit Frontend Scaffolding

**Ground Truth:** Verify `npx sv create` (SvelteKit scaffolding). Verify `@sveltejs/adapter-static` in `svelte.config.js` produces static build in `build/`. Verify `force-graph` npm package exists and exports `ForceGraph`.

**Provides:** Working SvelteKit app skeleton with split-pane layout, buildable to static files.

**Requires:** Node.js 20 (confirmed available).

**Integration test:** `npm run build` produces `frontend/build/index.html`.

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/svelte.config.js`
- Create: `frontend/vite.config.ts`
- Create: `frontend/src/app.html`
- Create: `frontend/src/app.css`
- Create: `frontend/src/routes/+page.svelte`
- Create: `frontend/src/routes/+layout.js`
- Create: `frontend/src/lib/stores/chat.ts`
- Create: `frontend/src/lib/stores/graph.ts`
- Create: `frontend/src/lib/stores/filters.ts`
- Create: `frontend/src/lib/api.ts`

### Steps:

- [ ] **Step 1: Create SvelteKit project**

Run:
```bash
cd /Users/rstarzl/Documents/GitHub/DOE_RedTeam
mkdir -p frontend && cd frontend
npm create svelte@latest . -- --template skeleton --types typescript --no-add-ons
npm install
npm install -D @sveltejs/adapter-static
npm install force-graph
```

- [ ] **Step 2: Configure static adapter**

Write `frontend/svelte.config.js`:
```javascript
import adapter from '@sveltejs/adapter-static';

/** @type {import('@sveltejs/kit').Config} */
const config = {
    kit: {
        adapter: adapter({
            pages: 'build',
            assets: 'build',
            fallback: 'index.html',
        }),
    },
};

export default config;
```

Write `frontend/vite.config.ts`:
```typescript
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
    plugins: [sveltekit()],
    server: {
        proxy: {
            '/api': 'http://localhost:8000',
        },
    },
});
```

Write `frontend/src/routes/+layout.js`:
```javascript
export const prerender = true;
export const ssr = false;
```

- [ ] **Step 3: Create app shell and global styles**

Write `frontend/src/app.css` — dark theme matching the mockup.

Write `frontend/src/app.html` with standard SvelteKit template.

- [ ] **Step 4: Create Svelte stores**

Write `frontend/src/lib/stores/chat.ts`, `graph.ts`, `filters.ts` with Svelte 5 runes ($state).

Write `frontend/src/lib/api.ts` with `fetchSSE()` helper for consuming SSE streams.

- [ ] **Step 5: Create main page with split-pane layout**

Write `frontend/src/routes/+page.svelte` — the 40/60 split layout importing ChatPanel and GraphPanel components (initially as placeholders).

- [ ] **Step 6: Verify build**

Run:
```bash
cd /Users/rstarzl/Documents/GitHub/DOE_RedTeam/frontend
npm run build
ls build/index.html
```
Expected: File exists

- [ ] **Step 7: Commit**

```bash
git add frontend/
git commit -m "feat: scaffold SvelteKit frontend with split-pane layout"
```

---

## Task 8: Frontend Components — ChatPanel + GraphPanel

**Ground Truth:** Verify `force-graph` default export creates a canvas-based graph when called with `ForceGraph()(container)`. Verify `EventSource` API or `fetch` with `ReadableStream` for SSE consumption. Verify Svelte 5 `$state` rune syntax.

**Provides:** `ChatPanel.svelte` (chat input, message display, SSE streaming, retrieval badges), `GraphPanel.svelte` (force-graph rendering, node click, highlight), `RetrievalBadges.svelte`, `ContractList.svelte`.

**Requires:** Task 7 (SvelteKit scaffolding + stores + api.ts).

**Integration test:** `npm run build` succeeds. Opening the built page in a browser shows the split layout (even without backend — graceful empty state).

**Files:**
- Create: `frontend/src/lib/components/ChatPanel.svelte`
- Create: `frontend/src/lib/components/GraphPanel.svelte`
- Create: `frontend/src/lib/components/RetrievalBadges.svelte`
- Create: `frontend/src/lib/components/ContractList.svelte`

### Steps:

- [ ] **Step 1: Implement ChatPanel.svelte**

Chat input, message rendering, SSE token streaming, retrieval badges display, contract list.

- [ ] **Step 2: Implement GraphPanel.svelte**

force-graph initialization on mount, node coloring by type, edge thickness by weight, click-to-expand, highlight support.

- [ ] **Step 3: Implement RetrievalBadges.svelte and ContractList.svelte**

Small presentational components.

- [ ] **Step 4: Wire components into +page.svelte**

Import ChatPanel and GraphPanel, connect via shared stores.

- [ ] **Step 5: Verify build**

Run: `cd frontend && npm run build`
Expected: No errors

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/components/
git commit -m "feat: add ChatPanel and GraphPanel components"
```

---

## Task 9: Frontend Components — Recipe + Toolbar + ProcessChain

**Ground Truth:** Verify SSE event types: `phase`, `round`, `converged`, `token`, `recipe_step`, `done`.

**Provides:** `RecipeCard.svelte` (recipe step rendering), `ProcessChain.svelte` (visual step sequence), `Toolbar.svelte` (filters + deep research button).

**Requires:** Task 8 (ChatPanel, GraphPanel, stores).

**Integration test:** `npm run build` succeeds with all components.

**Files:**
- Create: `frontend/src/lib/components/RecipeCard.svelte`
- Create: `frontend/src/lib/components/ProcessChain.svelte`
- Create: `frontend/src/lib/components/Toolbar.svelte`

### Steps:

- [ ] **Step 1: Implement Toolbar.svelte**

Fiscal year range, min dollar threshold, community dropdown, Deep Research toggle.

- [ ] **Step 2: Implement ProcessChain.svelte**

Renders `recipe_step` events as horizontal step flow with arrows.

- [ ] **Step 3: Implement RecipeCard.svelte**

Structured recipe output: steps with contractor names, dollar amounts, descriptions.

- [ ] **Step 4: Wire into +page.svelte**

Add Toolbar to top, integrate RecipeCard and ProcessChain into ChatPanel output.

- [ ] **Step 5: Final build**

Run: `cd frontend && npm run build`
Expected: Success, `build/index.html` exists

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/components/ frontend/src/routes/
git commit -m "feat: add RecipeCard, ProcessChain, and Toolbar components"
```

---

## Task 10: Docker Setup

**Ground Truth:** Verify `docker build --target` for multi-stage builds. Verify `docker compose up` with `volumes` mount syntax. Verify `host.docker.internal` resolves inside Docker Desktop for Mac.

**Provides:** `Dockerfile` (multi-stage: Node build + Python runtime), `docker-compose.yml`, `.dockerignore`.

**Requires:** Tasks 1-9 (all backend and frontend code).

**Integration test:** `docker compose build` succeeds. `docker compose up -d && curl http://localhost:8000/api/health` returns JSON.

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `.dockerignore`

### Steps:

- [ ] **Step 1: Create .dockerignore**

```
data/
chroma_db/
doe_contracts.db
*.pkl
*.db
node_modules/
frontend/build/
__pycache__/
.git/
.superpowers/
FY*.zip
FY*.csv
```

- [ ] **Step 2: Create multi-stage Dockerfile**

```dockerfile
# Stage 1: Build SvelteKit
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Stage 2: Python runtime
FROM python:3.12-slim
WORKDIR /app

COPY backend/requirements.txt backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY --from=frontend-build /app/frontend/build /app/frontend/build

ENV DB_PATH=/data/doe_contracts.db
ENV GRAPH_PATH=/data/graph.pkl
ENV CHROMA_PATH=/data/chroma_db
ENV OLLAMA_HOST=http://host.docker.internal:11434
ENV OLLAMA_MODEL=dolphin3
ENV STATIC_DIR=/app/frontend/build

EXPOSE 8000
CMD ["uvicorn", "backend.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: Create docker-compose.yml**

```yaml
services:
  app:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./doe_contracts.db:/data/doe_contracts.db:ro
      - ./chroma_db:/data/chroma_db:ro
      - ./graph.pkl:/data/graph.pkl:ro
      - ./topics.db:/data/topics.db
    environment:
      - OLLAMA_HOST=${OLLAMA_HOST:-http://host.docker.internal:11434}
      - OLLAMA_MODEL=${OLLAMA_MODEL:-dolphin3}
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

- [ ] **Step 4: Build and test**

Run:
```bash
# First build the graph pickle (needed for Docker volume mount)
cd /Users/rstarzl/Documents/GitHub/DOE_RedTeam
python3 -m backend.build_graph --db doe_contracts.db --output graph.pkl

# Build Docker image
docker compose build

# Start container
docker compose up -d

# Test health endpoint
curl http://localhost:8000/api/health
```

Expected: `{"status": "ready", ...}`

- [ ] **Step 5: Commit**

```bash
git add Dockerfile docker-compose.yml .dockerignore
git commit -m "feat: add Docker setup with multi-stage build"
```

---

## Task 11: Integration Test — Full Stack

**Ground Truth:** All endpoints respond correctly with the real `doe_contracts.db` data.

**Provides:** Verified working system end-to-end.

**Requires:** Tasks 1-10.

**Integration test:** Full round-trip: build graph → start container → query chat → verify response includes contracts.

### Steps:

- [ ] **Step 1: Build the knowledge graph from real data**

Run:
```bash
cd /Users/rstarzl/Documents/GitHub/DOE_RedTeam
python3 -m backend.build_graph --db doe_contracts.db --output graph.pkl
```
Expected: `graph.pkl` created, stats show ~5K recipients, ~1K PSC, ~500 NAICS

- [ ] **Step 2: Start the full stack**

Run:
```bash
docker compose up -d
sleep 5
curl http://localhost:8000/api/health
```
Expected: `{"status": "ready", "graph_loaded": true, "ollama_available": true, "fts5": true}`

- [ ] **Step 3: Test graph endpoint with real data**

Run: `curl "http://localhost:8000/api/graph?entity=recipient:SANDIA%20NATIONAL%20LABORATORIES&hops=1" | python3 -m json.tool | head -20`
Expected: JSON with nodes and edges for Sandia's network

- [ ] **Step 4: Test search endpoint**

Run: `curl "http://localhost:8000/api/search?q=solid+state+battery&mode=hybrid" | python3 -m json.tool | head -30`
Expected: Contracts with sources array containing "vector" and/or "keyword"

- [ ] **Step 5: Test chat endpoint (SSE)**

Run: `curl -N -X POST http://localhost:8000/api/chat -H "Content-Type: application/json" -d '{"messages":[{"role":"user","content":"What are the top battery research contractors?"}]}' | head -20`
Expected: SSE events: `event: retrieval`, `event: token`, `event: done`

- [ ] **Step 6: Open browser and verify UI**

Open `http://localhost:8000` in browser. Verify:
- Split-pane layout renders
- Graph panel shows nodes (may be empty until a query)
- Chat input works
- Typing a query streams a response

- [ ] **Step 7: Commit any integration fixes**

```bash
git add -A
git commit -m "fix: integration adjustments for full-stack testing"
```

---

## Task 12: Topic Extraction Script

**Ground Truth:** Verify Ollama `/api/chat` with `stream: false` for topic extraction. Verify SQLite `INSERT OR IGNORE` for idempotent topic storage.

**Provides:** `backend/extract_topics.py` as CLI script and importable module. Creates/populates `topics.db` with extracted topics from contract descriptions. Also provides the `/api/topics/extract` SSE endpoint in server.py.

**Requires:** Task 1 (`OllamaClient`), Task 3 (`build_graph.py` for graph rebuild after extraction).

**Integration test:** Run `extract_topics(sample_db, topics_db_path, ollama)` on sample data → `topics.db` contains at least 1 topic with linked contract keys.

**Files:**
- Create: `backend/extract_topics.py`
- Create: `tests/test_extract_topics.py`
- Modify: `backend/server.py` — add `/api/topics/extract` endpoint

### Steps:

- [ ] **Step 1: Write failing test**

```python
# tests/test_extract_topics.py
import tempfile
import os
import sqlite3
import pytest
from unittest.mock import AsyncMock
from backend.extract_topics import create_topics_db, extract_topics_batch

def test_create_topics_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    try:
        create_topics_db(path)
        conn = sqlite3.connect(path)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = [t[0] for t in tables]
        assert "topics" in table_names
        assert "topic_contracts" in table_names
        conn.close()
    finally:
        os.unlink(path)

@pytest.mark.asyncio
async def test_extract_topics_batch(sample_db):
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        topics_path = f.name
    try:
        create_topics_db(topics_path)
        mock_ollama = AsyncMock()
        mock_ollama.generate.return_value = json.dumps([
            {"topic": "solid electrolyte fabrication", "description": "Making solid electrolytes"},
            {"topic": "ceramic characterization", "description": "Testing ceramics"}
        ])
        stats = await extract_topics_batch(
            db_path=sample_db,
            topics_db_path=topics_path,
            ollama=mock_ollama,
            batch_size=5,
            limit=5,
        )
        assert stats["processed"] > 0
        assert stats["topics_created"] > 0
        conn = sqlite3.connect(topics_path)
        topics = conn.execute("SELECT * FROM topics").fetchall()
        assert len(topics) > 0
        conn.close()
    finally:
        os.unlink(topics_path)

import json
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_extract_topics.py -v`
Expected: FAIL

- [ ] **Step 3: Implement extract_topics.py**

```python
# backend/extract_topics.py
"""Extract topics from contract descriptions using Dolphin3 via Ollama."""
import argparse
import asyncio
import json
import sqlite3
from typing import AsyncGenerator
from backend.ollama_client import OllamaClient

EXTRACT_PROMPT = """Extract 1-3 specific technical topics from this DOE contract description.
Return ONLY a JSON array of objects with "topic" (short name) and "description" (one sentence).

Description: "{description}"

Example output: [{{"topic": "garnet ceramic sintering", "description": "High-temperature sintering of LLZO garnet ceramics for solid electrolytes"}}]"""


def create_topics_db(path: str):
    """Create topics.db schema if not exists."""
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS topics (
            topic_id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_name TEXT NOT NULL UNIQUE,
            topic_description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS topic_contracts (
            topic_id INTEGER REFERENCES topics(topic_id),
            contract_key TEXT NOT NULL,
            confidence REAL DEFAULT 1.0,
            PRIMARY KEY (topic_id, contract_key)
        );
        CREATE TABLE IF NOT EXISTS extraction_log (
            contract_key TEXT PRIMARY KEY,
            extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_topic_name ON topics(topic_name);
        CREATE INDEX IF NOT EXISTS idx_topic_contract ON topic_contracts(contract_key);
    """)
    conn.commit()
    conn.close()


async def extract_topics_batch(
    db_path: str,
    topics_db_path: str,
    ollama: OllamaClient,
    batch_size: int = 100,
    limit: int | None = None,
) -> dict:
    """Extract topics from unprocessed contract descriptions. Returns stats."""
    create_topics_db(topics_db_path)

    conn = sqlite3.connect(db_path)
    topics_conn = sqlite3.connect(topics_db_path)

    # Get already-processed keys
    processed = set(
        r[0] for r in topics_conn.execute("SELECT contract_key FROM extraction_log").fetchall()
    )

    # Get unprocessed descriptions
    rows = conn.execute(
        "SELECT contract_transaction_unique_key, transaction_description "
        "FROM contracts WHERE transaction_description IS NOT NULL"
    ).fetchall()
    conn.close()

    unprocessed = [(k, d) for k, d in rows if k not in processed]
    if limit:
        unprocessed = unprocessed[:limit]

    total_processed = 0
    total_topics = 0

    for i in range(0, len(unprocessed), batch_size):
        batch = unprocessed[i:i + batch_size]
        for key, description in batch:
            try:
                prompt = EXTRACT_PROMPT.format(description=description[:500])
                response = await ollama.generate(prompt)
                topics = json.loads(response)
                if not isinstance(topics, list):
                    topics = []
            except (json.JSONDecodeError, Exception):
                topics = []

            for t in topics:
                topic_name = t.get("topic", "").strip().lower()
                topic_desc = t.get("description", "")
                if not topic_name:
                    continue

                # Upsert topic
                topics_conn.execute(
                    "INSERT OR IGNORE INTO topics (topic_name, topic_description) VALUES (?, ?)",
                    (topic_name, topic_desc),
                )
                topic_id = topics_conn.execute(
                    "SELECT topic_id FROM topics WHERE topic_name = ?", (topic_name,)
                ).fetchone()[0]

                # Link to contract
                topics_conn.execute(
                    "INSERT OR IGNORE INTO topic_contracts (topic_id, contract_key) VALUES (?, ?)",
                    (topic_id, key),
                )
                total_topics += 1

            # Mark as processed
            topics_conn.execute(
                "INSERT OR IGNORE INTO extraction_log (contract_key) VALUES (?)", (key,)
            )
            total_processed += 1

        topics_conn.commit()

    topics_conn.close()
    return {"processed": total_processed, "topics_created": total_topics}


async def extract_topics_stream(
    db_path: str, topics_db_path: str, ollama: OllamaClient,
    batch_size: int = 100, limit: int | None = None,
) -> AsyncGenerator[dict, None]:
    """Streaming version for SSE endpoint."""
    yield {"event": "phase", "data": {"phase": "extracting"}}
    stats = await extract_topics_batch(db_path, topics_db_path, ollama, batch_size, limit)
    yield {"event": "done", "data": stats}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract topics from DOE contracts")
    parser.add_argument("--db", default="doe_contracts.db")
    parser.add_argument("--topics-db", default="topics.db")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--ollama-host", default="http://localhost:11434")
    parser.add_argument("--model", default="dolphin3")
    args = parser.parse_args()

    ollama = OllamaClient(base_url=args.ollama_host, model=args.model)
    stats = asyncio.run(extract_topics_batch(
        args.db, args.topics_db, ollama, args.batch_size, args.limit
    ))
    print(f"Extraction complete: {stats}")
```

- [ ] **Step 4: Add /api/topics/extract endpoint to server.py**

Add to `backend/server.py` inside `create_app()`:

```python
    # --- Topic Extraction (SSE) ---
    class TopicExtractRequest(BaseModel):
        batch_size: int = 100
        limit: int | None = None
        rebuild_graph: bool = False

    @app.post("/api/topics/extract")
    async def extract_topics(req: TopicExtractRequest):
        from backend.extract_topics import extract_topics_stream
        topics_db = os.environ.get("TOPICS_DB_PATH", "/data/topics.db")
        ollama = state["ollama"]

        async def event_stream():
            async for event in extract_topics_stream(
                DB_PATH, topics_db, ollama, req.batch_size, req.limit
            ):
                yield {"event": event["event"], "data": json.dumps(event["data"])}

        return EventSourceResponse(event_stream())
```

- [ ] **Step 5: Run tests**

Run: `python3 -m pytest tests/test_extract_topics.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/extract_topics.py tests/test_extract_topics.py backend/server.py
git commit -m "feat: add topic extraction script and /api/topics/extract endpoint"
```

---

## Execution Summary

| Task | Component | Dependencies | ~Effort |
|------|-----------|-------------|---------|
| 1 | Ollama Client + Scaffolding | None | Small |
| 2 | FTS5 Setup | Task 1 fixtures | Small |
| 3 | Graph Engine + Builder | Task 1 fixtures | Medium |
| 4 | Hybrid Retriever | Tasks 2, 3 | Medium |
| 5 | Recipe Engine | Tasks 1, 4 | Medium |
| 6 | FastAPI Server | Tasks 1-5 | Medium |
| 7 | Frontend Scaffolding | Node.js | Small |
| 8 | ChatPanel + GraphPanel | Task 7 | Large |
| 9 | Recipe + Toolbar + ProcessChain | Task 8 | Medium |
| 10 | Docker Setup | Tasks 1-9 | Small |
| 11 | Integration Testing | Tasks 1-10 | Medium |
| 12 | Topic Extraction | Tasks 1, 3 | Medium |

**Parallelizable:** Tasks 2 + 3 can run in parallel. Tasks 7-9 (frontend) can run in parallel with Tasks 4-6 (backend) once scaffolding is done. Task 12 can run after Tasks 1+3. Task 10 depends on all others.
