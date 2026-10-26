# Command Console — Routed Retrieval + Conversation Memory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reattach the orphaned 4-lane HybridRetriever to production chat, add an intent router that dispatches aggregate questions to a SQL path, and replace the 6-turn history cap with a real conversation memory layer (verbatim + rolling summary + entity tracker).

**Architecture:** 3-stage chat pipeline. (1) `classify_intent` (LLM with structured output) routes the query to one of `{aggregate, entity_narrative, action, smalltalk}`. (2) Each intent dispatches to the right tool: `aggregate_contracts()` (SQL GROUP BY) for aggregates, `HybridRetriever.search()` (existing 4-lane RAG) for narratives, the existing MAP_CMD path for actions, no retrieval for smalltalk. (3) Prompt is built from system prompt + retrieved context + token-budgeted history (or `ConversationState` once Task 6 lands) + current query, then streamed via Hermes-4-405B. Per-turn JSONL logging (`logs/atlas_chat.jsonl`) is added in Task 0 so every later task can be diagnosed against real data.

**Tech Stack:** FastAPI/Starlette, Pydantic v2, sqlite3 (250,125-row `doe_contracts.db` with FTS5), ChromaDB (existing 247,819-embedding `doe_contracts` collection), `backend.hybrid_retriever.HybridRetriever`, `backend.mercury_client.HermesClient` (Hermes-4-405B with `chat_structured` for JSON schema output), `backend.ollama_client.OllamaClient` (nomic-embed-text embeddings).

**Pre-flight ground truth (verified in design phase):**
- Production chat handler is `test_atlas_server.py:1087-1157` (`@app.post("/api/atlas-chat")`)
- Existing model: `class AtlasChatRequest(BaseModel)` at `test_atlas_server.py:229-233` — fields `query`, `messages`, `contractor_count`, `data_context`
- The 6-turn cap is at `test_atlas_server.py:1100`: `history = list(req.messages[-6:])`
- The 500-char truncation is at line 1107
- `HermesClient` exports `chat_structured(messages, schema)` at `backend/mercury_client.py:106-135` (uses OpenAI `response_format: json_schema` strict mode)
- `HybridRetriever.__init__(db_path, graph_engine=None, chroma_path=None, ollama=None)` — `backend/hybrid_retriever.py:40-58`
- `HybridRetriever.search(query, n_results=15, use_reranker=True) → HybridResults` returning `.contracts: list[ContractResult]` with fields `key, description, recipient, obligation, fiscal_year, psc, naics, sources, rrf_score`
- `chroma_db/` has the `doe_contracts` collection with 247,819 embeddings — verified via `sqlite3 chroma_db/chroma.sqlite3`
- `chromadb` is **NOT** in `requirements.txt` — Task 1 must add it
- JSONL logging precedent: `test_atlas_server.py:1160-1210` (`/api/client-error` endpoint) — pattern: `BASE / "logs" / *.jsonl`, `mkdir(parents=True, exist_ok=True)`, append-only, in-process rate limit + size cap, behind `AuthMiddleware`
- Frontend chat send is `frontend/static/contractor-map.html:6076-6114`; payload built around line 6076-6081
- Frontend telemetry already generates `crypto.randomUUID()` session id — Task 6 lifts that to module scope and adds it to chat payload

---

## Task 0: JSONL chat logging (no behavior change)

**Files:**
- Create: `tests/test_atlas_chat_logging.py`
- Modify: `test_atlas_server.py` (add log writer + call site inside `atlas_chat`)
- Modify: `.gitignore` (add `logs/atlas_chat.jsonl` if not already covered by `logs/*.jsonl`)

**Ground Truth (verify before coding):**
- `test_atlas_server.py` lines 1160-1210 — confirm `_CLIENT_ERROR_LOG` pattern, `time` and `collections` already imported at line 1172-1173
- `_ATLAS_CHAT_LOG` will follow the same `BASE / "logs" / "atlas_chat.jsonl"` shape
- Verify `.gitignore` already has `logs/*.jsonl` (added in the previous robustness commit cluster)
- Run `python3 -c "import json, time; print('ok')"` to confirm the stdlib modules used in this task exist (they always do, but ground-truth says verify imports)

**Provides:**
- `_ATLAS_CHAT_LOG: pathlib.Path` — module-level path constant
- `def _log_chat_turn(record: dict) -> None` — module-level function that JSONL-appends a record (truncates `full_messages` and `response_text` to safe sizes)
- A new entry written to `logs/atlas_chat.jsonl` for every successful chat turn
- Test fixture pattern: tests can import `_ATLAS_CHAT_LOG` and `_log_chat_turn` from `test_atlas_server`

**Requires:** nothing (Task 0 is the foundation)

**Integration test spec:** A pytest test that imports `app` from `test_atlas_server`, uses `httpx.AsyncClient` with `ASGITransport` to POST to `/api/atlas-chat` with a monkeypatched `hermes.chat_stream` returning a fixed token sequence, then asserts that `logs/atlas_chat.jsonl` contains exactly one new line with the expected JSON shape (`session_id`, `query`, `response_text`, `response_time_ms`, etc.).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_atlas_chat_logging.py
import asyncio
import json
import os
import pathlib
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def clean_log(tmp_path, monkeypatch):
    """Redirect _ATLAS_CHAT_LOG to a temp file for the test."""
    import test_atlas_server as srv
    log_path = tmp_path / "atlas_chat.jsonl"
    monkeypatch.setattr(srv, "_ATLAS_CHAT_LOG", log_path)
    yield log_path


async def _fake_stream(messages, *args, **kwargs):
    for tok in ["Hello", " ", "world"]:
        yield tok


@pytest.mark.asyncio
async def test_chat_turn_is_logged(clean_log, monkeypatch):
    import test_atlas_server as srv
    monkeypatch.setattr(srv.hermes, "is_available", lambda: True)
    monkeypatch.setattr(srv.hermes, "chat_stream", _fake_stream)

    payload = {
        "query": "what's up",
        "messages": [],
        "contractor_count": 2214,
        "data_context": "",
        "session_id": "test-session-123",
    }

    transport = ASGITransport(app=srv.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Bypass auth
        srv.SITE_PASSWORD = ""
        resp = await client.post("/api/atlas-chat", json=payload)
        assert resp.status_code == 200
        # Drain the SSE stream
        _ = resp.text

    assert clean_log.exists(), "log file should be created"
    lines = clean_log.read_text().strip().splitlines()
    assert len(lines) == 1, f"expected 1 log line, got {len(lines)}"
    record = json.loads(lines[0])
    assert record["session_id"] == "test-session-123"
    assert record["query"] == "what's up"
    assert "Hello world" in record["response_text"]
    assert record["response_time_ms"] >= 0
    assert "full_messages" in record
    assert isinstance(record["full_messages"], list)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest tests/test_atlas_chat_logging.py -v 2>&1 | tail -20
```
Expected: FAIL with `AttributeError: module 'test_atlas_server' has no attribute '_ATLAS_CHAT_LOG'` (or similar). Also expected: the request will fail because `session_id` isn't yet on `AtlasChatRequest` — that's fine, we're confirming the wiring needs to happen.

- [ ] **Step 3: Add `session_id` to `AtlasChatRequest`**

In `test_atlas_server.py`, edit the existing class at line 229-233:

```python
class AtlasChatRequest(BaseModel):
    query: str
    messages: list[dict] = []
    contractor_count: int = 0
    data_context: str = ""
    session_id: str = ""  # client-generated UUID; reused from telemetry IIFE
```

- [ ] **Step 4: Add the log path, log writer, and dependencies**

In `test_atlas_server.py`, after the existing `_CLIENT_ERROR_LOG` block (around line 1167) — add a parallel block. Note: `pathlib`, `time`, `json`, `collections` are already imported.

```python
# ── Chat conversation logging ──
# Captures every chat turn with the full prompt + response so we can diagnose
# retrieval / memory failures from real usage. Append-only JSONL.
# Behind AuthMiddleware (same as /api/client-error).
_ATLAS_CHAT_LOG = BASE / "logs" / "atlas_chat.jsonl"
_ATLAS_CHAT_LOG.parent.mkdir(parents=True, exist_ok=True)

_CHAT_LOG_MAX_RESPONSE_CHARS = 16384
_CHAT_LOG_MAX_FIELD_CHARS = 4096


def _log_chat_turn(record: dict) -> None:
    """Append one chat turn to logs/atlas_chat.jsonl with size caps."""
    safe = dict(record)
    if "response_text" in safe and isinstance(safe["response_text"], str):
        safe["response_text"] = safe["response_text"][:_CHAT_LOG_MAX_RESPONSE_CHARS]
    if "full_messages" in safe and isinstance(safe["full_messages"], list):
        safe["full_messages"] = [
            {
                "role": m.get("role", ""),
                "content": (m.get("content", "") or "")[:_CHAT_LOG_MAX_FIELD_CHARS],
            }
            for m in safe["full_messages"]
        ]
    safe["server_timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    try:
        with open(_ATLAS_CHAT_LOG, "a") as f:
            f.write(json.dumps(safe) + "\n")
    except Exception:
        pass  # logging must never break chat
```

- [ ] **Step 5: Call `_log_chat_turn` from inside `atlas_chat` after the stream completes**

Edit `test_atlas_server.py` `atlas_chat` (currently at lines 1087-1157). Wrap the stream so that we accumulate the response text and call `_log_chat_turn` once after the stream finishes. Find the existing `async def stream():` definition starting around line 1110 and modify the closure to capture the start time and call the logger at the end.

Replace the existing `async def stream():` body with:

```python
    start_time = time.time()
    accumulated_response: list[str] = []

    async def stream():
        use_hermes = hermes.is_available()
        response_parts = []
        last_emitted = ""
        error_message: str | None = None

        try:
            gen = hermes.chat_stream(messages) if use_hermes else ollama.chat_stream(messages)
            async for token in gen:
                response_parts.append(token)
                text_so_far = "".join(response_parts)

                text_so_far, cmds = extract_map_actions(text_so_far, final=False)
                response_parts = [text_so_far]

                for cmd in cmds:
                    yield f"data: {json.dumps({'type': 'map_command', 'command': cmd})}\n\n"

                if (
                    "MAP_CMD:" in text_so_far
                    or _ends_with_partial_map_prefix(text_so_far)
                    or _has_unclosed_code_fence(text_so_far)
                    or _ends_with_partial_fence(text_so_far)
                ):
                    continue

                if len(text_so_far) > len(last_emitted):
                    diff = text_so_far[len(last_emitted):]
                    yield f"data: {json.dumps({'type': 'token', 'content': diff})}\n\n"
                    last_emitted = text_so_far

            final_text = "".join(response_parts)
            final_text, cmds = extract_map_actions(final_text, final=True)
            for cmd in cmds:
                yield f"data: {json.dumps({'type': 'map_command', 'command': cmd})}\n\n"
            if len(final_text) > len(last_emitted):
                diff = final_text[len(last_emitted):]
                if diff.strip():
                    yield f"data: {json.dumps({'type': 'token', 'content': diff})}\n\n"
            accumulated_response.append(final_text)

        except Exception as e:
            error_message = str(e)
            yield f"data: {json.dumps({'type': 'error', 'message': error_message})}\n\n"

        yield "data: [DONE]\n\n"

        # Log the turn (after the stream is fully drained)
        _log_chat_turn({
            "session_id": req.session_id,
            "query": req.query,
            "intent_classification": None,  # filled by Task 3
            "retrieval_path": "legacy_substring",  # updated in Task 2
            "retrieval_results_count": 0,
            "retrieval_results_preview": [],
            "prompt_tokens_estimate": sum(len(m.get("content", "")) for m in messages) // 4,
            "history_tokens_estimate": sum(
                len(m.get("content", "")) for m in messages if m.get("role") != "system"
            ) // 4,
            "full_messages": messages,
            "response_text": "".join(accumulated_response),
            "response_time_ms": int((time.time() - start_time) * 1000),
            "error": error_message,
        })
```

- [ ] **Step 6: Run test to verify it passes**

```bash
python3 -m pytest tests/test_atlas_chat_logging.py -v 2>&1 | tail -20
```
Expected: `1 passed`. The log file is written, the record has all the expected fields, the existing chat behavior is unchanged.

- [ ] **Step 7: Run the existing browser-compat suite (no regressions)**

```bash
python3 -m pytest tests/test_atlas_browser_compat.py -v --browser chromium 2>&1 | tail -20
```
Expected: same pass count as before this task (currently 23 functions × 1 browser = ~25 tests). Confirms the chat handler changes didn't break anything.

- [ ] **Step 8: Commit**

```bash
git add tests/test_atlas_chat_logging.py test_atlas_server.py
git commit -m "feat: JSONL chat conversation logging — Task 0 of RAG/memory plan"
```

---

## Task 1: chromadb dependency + smoke test orphaned retriever

**Files:**
- Modify: `requirements.txt`
- Create: `tests/test_chroma_smoke.py`

**Ground Truth (verify before coding):**
- `chromadb` is NOT in `requirements.txt` (verified)
- `chroma_db/` exists at repo root, contains `chroma.sqlite3` (284MB, last modified 2026-03-30)
- The collection is named `doe_contracts` with 247,819 embeddings (verified via direct sqlite query)
- `backend.hybrid_retriever.HybridRetriever.__init__` signature: `(db_path, graph_engine=None, chroma_path=None, ollama=None)`
- `OllamaClient` is at `backend.ollama_client.OllamaClient` and exposes `embed_sync(texts: list[str]) -> list[list[float]]` — used by `search_vector`
- Run `python3 -c "import chromadb; print(chromadb.__version__)"` BEFORE the task to know whether chromadb is currently installed locally (likely yes from prior dev work, even though it's not in requirements.txt)

**Provides:**
- `chromadb>=0.4.0` declared in `requirements.txt` (so Railway installs it)
- A passing smoke test that proves `HybridRetriever` initializes against the real `chroma_db/` and returns non-zero results for a known query
- Confidence to proceed with Task 2 (wiring it into atlas_chat)

**Requires:** Task 0 (only because the commit must land after Task 0 — no code dependency)

**Integration test spec:** A pytest test that instantiates `HybridRetriever(db_path="doe_contracts.db", chroma_path="chroma_db", ollama=OllamaClient())` and runs `search_vector("nuclear waste cleanup")`. Asserts non-empty result. **Marked as `@pytest.mark.integration`** and skipped if `chroma_db/` doesn't exist (so CI without the chroma directory still passes).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_chroma_smoke.py
import os
import pytest
import pathlib

CHROMA_PATH = pathlib.Path(__file__).parent.parent / "chroma_db"
DB_PATH = pathlib.Path(__file__).parent.parent / "doe_contracts.db"

pytestmark = pytest.mark.skipif(
    not CHROMA_PATH.exists() or not DB_PATH.exists(),
    reason="chroma_db or doe_contracts.db not present in this environment",
)


def test_hybrid_retriever_initializes_against_real_chroma():
    from backend.hybrid_retriever import HybridRetriever
    from backend.ollama_client import OllamaClient

    retriever = HybridRetriever(
        db_path=str(DB_PATH),
        chroma_path=str(CHROMA_PATH),
        ollama=OllamaClient(),
    )
    assert retriever.chroma_collection is not None, (
        "expected chroma_collection 'doe_contracts' to load — "
        "either chromadb is not installed or the collection is missing"
    )
    assert retriever.chroma_collection.count() > 200_000, (
        f"expected ~247k embeddings, got {retriever.chroma_collection.count()}"
    )


def test_hybrid_retriever_returns_results_for_known_query():
    """Smoke test that the orphaned retriever still works end-to-end.
    
    Uses search_keyword (FTS5) instead of search_vector to avoid Ollama
    dependency in CI; vector search is verified by the test above (count > 0).
    """
    from backend.hybrid_retriever import HybridRetriever

    retriever = HybridRetriever(
        db_path=str(DB_PATH),
        chroma_path=str(CHROMA_PATH),
    )
    results = retriever.search_keyword("nuclear", limit=5)
    assert len(results) > 0, "FTS5 keyword search returned zero results for 'nuclear'"
    assert all("contract_transaction_unique_key" in r for r in results)
```

- [ ] **Step 2: Run test to verify it fails (or skips, if chromadb missing)**

```bash
python3 -m pytest tests/test_chroma_smoke.py -v 2>&1 | tail -20
```
Expected: either FAIL with `chromadb not installed` (most likely if requirements.txt is the source of truth) OR PASS (if chromadb was installed during prior dev work). Either outcome is informative.

- [ ] **Step 3: Add chromadb to requirements.txt**

Edit `requirements.txt`. Add this section at the end:

```
# Vector store for RAG (4-lane HybridRetriever in backend/hybrid_retriever.py)
chromadb>=0.4.22,<1.0.0
```

- [ ] **Step 4: Install and re-run smoke test**

```bash
pip install -r requirements.txt 2>&1 | tail -5
python3 -m pytest tests/test_chroma_smoke.py -v 2>&1 | tail -20
```
Expected: both tests PASS. `test_hybrid_retriever_initializes_against_real_chroma` confirms 247k+ embeddings; `test_hybrid_retriever_returns_results_for_known_query` confirms FTS5 works.

If the test fails because the FTS5 table is missing, that's a separate problem — fix it by running:
```bash
python3 -c "from backend.setup_fts import ensure_fts5; ensure_fts5('doe_contracts.db')"
```
Then re-run the test.

- [ ] **Step 5: Commit**

```bash
git add requirements.txt tests/test_chroma_smoke.py
git commit -m "feat: declare chromadb dep + smoke test orphaned HybridRetriever — Task 1"
```

---

## Task 2: Reattach HybridRetriever to atlas_chat

**Files:**
- Modify: `test_atlas_server.py` (add retriever singleton + dispatch in atlas_chat)
- Create: `tests/test_atlas_chat_retrieval.py`

**Ground Truth (verify before coding):**
- The pattern for prompt injection is at `backend/server.py:618-637`:
  ```python
  retriever = state["retriever"]
  results = await asyncio.to_thread(retriever.search, req.query)
  contract_context = "\n".join(
      f"- {c.recipient}: {c.description} (${c.obligation:,.0f})"
      for c in results.contracts[:20]
  )
  ```
- `asyncio.to_thread` is needed because `HybridRetriever.search` is sync (calls sync sqlite + sync ChromaDB)
- Move the retriever initialization to a lazy singleton so import-time failures don't break the server boot
- Failure modes to handle gracefully:
  - chromadb not installed (already handled in hybrid_retriever.py via try/except)
  - chroma_db/ directory missing
  - graph_engine.GraphEngine() fails to load (it loads a pickle from disk)
  - Ollama not running (vector search returns [])

**Provides:**
- Module-level `_retriever_singleton` and `def get_retriever() -> HybridRetriever | None`
- New `retrieval_context: str` block in the prompt (when retriever is available)
- `retrieval_path` field in chat log = `"hybrid_4lane"` when retriever fired, else `"legacy_substring"`

**Requires:** Task 0 (the chat log structure), Task 1 (chromadb dep declared and verified)

**Integration test spec:** A pytest test that monkeypatches `get_retriever()` to return a stub `HybridRetriever` whose `.search()` returns 3 fake `ContractResult` objects. POST a chat request, drain the SSE stream, then assert: (a) the log entry has `retrieval_path == "hybrid_4lane"`, (b) the log entry's `full_messages` contains a system message that includes "RELEVANT CONTRACT DATA:" and the 3 fake contractor recipient names.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_atlas_chat_retrieval.py
import json
import pytest
from dataclasses import dataclass
from httpx import ASGITransport, AsyncClient
from unittest.mock import MagicMock


@dataclass
class StubContract:
    key: str
    description: str
    recipient: str
    obligation: float
    fiscal_year: int = 2025
    psc: str = ""
    naics: str = ""
    sources: list = None
    rrf_score: float = 0.5


@dataclass
class StubResults:
    contracts: list
    retrieval_counts: dict = None
    graph_paths: dict = None


@pytest.fixture
def fake_retriever_chat(tmp_path, monkeypatch):
    import test_atlas_server as srv
    monkeypatch.setattr(srv, "_ATLAS_CHAT_LOG", tmp_path / "atlas_chat.jsonl")
    srv.SITE_PASSWORD = ""

    fake_results = StubResults(
        contracts=[
            StubContract(key="K1", description="Cybersecurity assessment for NNSA",
                         recipient="HONEYWELL FEDERAL MFG & TECH", obligation=12345678),
            StubContract(key="K2", description="Penetration testing services",
                         recipient="LOCKHEED MARTIN", obligation=987654),
            StubContract(key="K3", description="Network monitoring",
                         recipient="RAYTHEON", obligation=55555),
        ],
        retrieval_counts={"vector": 3, "keyword": 0, "graph": 0, "relationship": 0, "fused": 3},
        graph_paths={"nodes": [], "edges": []},
    )
    fake = MagicMock()
    fake.search.return_value = fake_results
    monkeypatch.setattr(srv, "_retriever_singleton", fake)
    monkeypatch.setattr(srv, "get_retriever", lambda: fake)

    async def fake_stream(messages, *args, **kwargs):
        for tok in ["Honeywell", " has", " contracts"]:
            yield tok

    monkeypatch.setattr(srv.hermes, "is_available", lambda: True)
    monkeypatch.setattr(srv.hermes, "chat_stream", fake_stream)
    return tmp_path / "atlas_chat.jsonl"


@pytest.mark.asyncio
async def test_chat_includes_retrieval_context_in_prompt(fake_retriever_chat):
    import test_atlas_server as srv
    payload = {"query": "tell me about Honeywell's cybersecurity",
               "session_id": "s1", "messages": [], "contractor_count": 2214, "data_context": ""}

    transport = ASGITransport(app=srv.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/atlas-chat", json=payload)
        assert resp.status_code == 200
        _ = resp.text  # drain

    log_path = fake_retriever_chat
    record = json.loads(log_path.read_text().strip().splitlines()[-1])
    assert record["retrieval_path"] == "hybrid_4lane"
    assert record["retrieval_results_count"] == 3

    # The system message should contain the retrieval context
    system_msg = record["full_messages"][0]
    assert system_msg["role"] == "system"
    assert "RELEVANT CONTRACT DATA" in system_msg["content"]
    assert "HONEYWELL" in system_msg["content"]
    assert "LOCKHEED" in system_msg["content"]
    assert "Cybersecurity assessment" in system_msg["content"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest tests/test_atlas_chat_retrieval.py -v 2>&1 | tail -20
```
Expected: FAIL — `get_retriever` doesn't exist yet on `test_atlas_server` module.

- [ ] **Step 3: Add the retriever singleton**

In `test_atlas_server.py`, after `hermes = HermesClient()` / `ollama = OllamaClient()` (around line 121-122), add:

```python
# ── Hybrid retriever (lazy singleton) ──
# The 4-lane RAG (vector + FTS5 + graph + relationship + RRF) lives in
# backend/hybrid_retriever.py. We initialize it lazily so import-time failures
# (missing chroma_db/, missing graph pickle, etc.) don't take down the server.
_retriever_singleton = None
_retriever_init_attempted = False


def get_retriever():
    """Return the HybridRetriever singleton, or None if init failed.
    
    Initialization is attempted ONCE per process. If it fails (chromadb
    missing, chroma_db/ missing, graph pickle missing, etc.) we log and
    return None — chat falls back to the legacy substring path.
    """
    global _retriever_singleton, _retriever_init_attempted
    if _retriever_init_attempted:
        return _retriever_singleton

    _retriever_init_attempted = True
    try:
        from backend.hybrid_retriever import HybridRetriever
        try:
            from backend.graph_engine import GraphEngine
            graph = GraphEngine()  # loads pickle from default location
        except Exception as e:
            print(f"[atlas-chat] graph engine unavailable, continuing without graph lane: {e}")
            graph = None
        retriever = HybridRetriever(
            db_path=str(BASE / "doe_contracts.db"),
            graph_engine=graph,
            chroma_path=str(BASE / "chroma_db"),
            ollama=ollama,
        )
        if retriever.chroma_collection is None and graph is None:
            print("[atlas-chat] retriever has no chroma + no graph; falling back to legacy substring")
            return None
        _retriever_singleton = retriever
        print(f"[atlas-chat] HybridRetriever initialized (chroma={retriever.chroma_collection is not None}, graph={graph is not None})")
        return _retriever_singleton
    except Exception as e:
        print(f"[atlas-chat] retriever init failed, falling back to legacy substring: {e}")
        return None
```

- [ ] **Step 4: Dispatch retrieval inside atlas_chat**

Edit the `atlas_chat` function. After building `system_content` (around line 1092), but BEFORE the `history = list(req.messages[-6:])` line, add the retrieval block:

```python
    # ── Retrieval (Task 2) ──
    # Try the 4-lane HybridRetriever first; fall back to the legacy substring path
    # in dataContext (sent by the frontend) on any failure.
    retriever = get_retriever()
    retrieval_path = "legacy_substring"
    retrieval_results_count = 0
    retrieval_results_preview: list[str] = []

    if retriever is not None:
        try:
            results = await asyncio.to_thread(retriever.search, req.query, 15, True)
            if results.contracts:
                contract_context = "\n".join(
                    f"- {c.recipient}: {c.description[:200]} (${c.obligation:,.0f})"
                    for c in results.contracts[:15]
                )
                system_content += (
                    "\n\nRELEVANT CONTRACT DATA (from 4-lane retrieval — vector + keyword + graph + relationship):\n"
                    + contract_context
                )
                retrieval_path = "hybrid_4lane"
                retrieval_results_count = len(results.contracts)
                retrieval_results_preview = [
                    f"{c.recipient}: {c.description[:80]}"
                    for c in results.contracts[:3]
                ]
        except Exception as e:
            print(f"[atlas-chat] retrieval failed mid-request, using legacy: {e}")
```

- [ ] **Step 5: Update the log entry to record the new fields**

In the `_log_chat_turn(...)` call inside `stream()` (added in Task 0), update the `retrieval_path`, `retrieval_results_count`, `retrieval_results_preview` fields to use the new variables:

```python
        _log_chat_turn({
            "session_id": req.session_id,
            "query": req.query,
            "intent_classification": None,  # filled by Task 3
            "retrieval_path": retrieval_path,
            "retrieval_results_count": retrieval_results_count,
            "retrieval_results_preview": retrieval_results_preview,
            ...  # (rest of the fields unchanged)
        })
```

- [ ] **Step 6: Run the test to verify it passes**

```bash
python3 -m pytest tests/test_atlas_chat_retrieval.py -v 2>&1 | tail -20
```
Expected: `1 passed`. The retrieval context is injected into the system message.

- [ ] **Step 7: Run the chroma smoke test + Task 0 logging test + browser-compat to confirm no regression**

```bash
python3 -m pytest tests/test_atlas_chat_logging.py tests/test_chroma_smoke.py tests/test_atlas_chat_retrieval.py -v 2>&1 | tail -25
python3 -m pytest tests/test_atlas_browser_compat.py --browser chromium -v 2>&1 | tail -10
```
Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add test_atlas_server.py tests/test_atlas_chat_retrieval.py
git commit -m "feat: reattach 4-lane HybridRetriever to production chat — Task 2"
```

---

## Task 3: Intent router via HermesClient.chat_structured

**Files:**
- Create: `backend/intent_router.py`
- Create: `tests/test_intent_router.py`
- Modify: `test_atlas_server.py` (call classify_intent before retrieval; record in log)

**Ground Truth (verify before coding):**
- `HermesClient.chat_structured(messages, schema, max_tokens)` is at `backend/mercury_client.py:106-135`. It posts to `/v1/chat/completions` with `response_format={"type": "json_schema", "json_schema": {"name": "structured_output", "strict": True, "schema": schema}}`. Returns `dict` (parsed JSON).
- The schema must be a valid JSON Schema dict (with `type`, `properties`, `required`, `additionalProperties: False` for strict mode).
- Pydantic v2 has `model_json_schema()` to generate JSON schemas from BaseModel classes — but strict mode requires `additionalProperties: False` which Pydantic doesn't always emit; we'll write the schema by hand for control.
- `Literal` is in `typing` (Python 3.8+)
- Don't import `IntentClassification` into `test_atlas_server.py` until the dispatch logic in Task 4 needs it; for Task 3 we just need `classify_intent` to work and be logged.

**Provides:**
- `backend/intent_router.py` exports:
  - `class IntentClassification(BaseModel)` with fields `intent`, `confidence`, `search_terms`, `filters`, `target_contractor`
  - `INTENT_SCHEMA: dict` — the JSON Schema passed to chat_structured
  - `async def classify_intent(query: str, hermes: HermesClient, recent_history: list[dict] | None = None) -> IntentClassification`
- `intent_classification` field in chat log now populated (was `None` after Task 0)

**Requires:** Task 2 (we now know the chat handler structure to inject the call into)

**Integration test spec:** A pytest test that monkeypatches `HermesClient.chat_structured` to return a fixed dict and asserts `classify_intent("who has contracts for nuclear waste", ...)` returns `IntentClassification(intent="aggregate", search_terms=["nuclear waste"], ...)`. A second test asserts the schema is valid JSON Schema (no unknown keys, strict mode compatible). A third test runs against the LIVE Hermes API and asserts that 8/10 of a fixed query set classify into the expected intent (marked `@pytest.mark.live` and skipped without `NOUS_API_KEY`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_intent_router.py
import os
import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.intent_router import (
    classify_intent,
    IntentClassification,
    INTENT_SCHEMA,
)


def test_intent_schema_is_strict_compatible():
    """The schema must satisfy OpenAI strict-mode requirements:
    - top-level type=object
    - additionalProperties: False at every object level
    - all properties listed in 'required'
    """
    assert INTENT_SCHEMA["type"] == "object"
    assert INTENT_SCHEMA.get("additionalProperties") is False
    assert set(INTENT_SCHEMA["required"]) == set(INTENT_SCHEMA["properties"].keys())


@pytest.mark.asyncio
async def test_classify_intent_aggregate():
    fake_hermes = MagicMock()
    fake_hermes.chat_structured = AsyncMock(return_value={
        "intent": "aggregate",
        "confidence": 0.95,
        "search_terms": ["nuclear waste"],
        "filters": {},
        "target_contractor": None,
    })
    result = await classify_intent("who has contracts for nuclear waste", fake_hermes)
    assert isinstance(result, IntentClassification)
    assert result.intent == "aggregate"
    assert result.search_terms == ["nuclear waste"]
    assert result.target_contractor is None


@pytest.mark.asyncio
async def test_classify_intent_entity_narrative():
    fake_hermes = MagicMock()
    fake_hermes.chat_structured = AsyncMock(return_value={
        "intent": "entity_narrative",
        "confidence": 0.88,
        "search_terms": ["cybersecurity", "posture"],
        "filters": {},
        "target_contractor": "Honeywell Federal Manufacturing",
    })
    result = await classify_intent("tell me about honeywell's cybersecurity posture", fake_hermes)
    assert result.intent == "entity_narrative"
    assert result.target_contractor == "Honeywell Federal Manufacturing"


@pytest.mark.asyncio
async def test_classify_intent_handles_malformed_response():
    """If Hermes returns garbage, we default to entity_narrative (the safe path
    that uses retrieval) rather than crashing."""
    fake_hermes = MagicMock()
    fake_hermes.chat_structured = AsyncMock(side_effect=ValueError("bad json"))
    result = await classify_intent("anything", fake_hermes)
    assert result.intent == "entity_narrative"
    assert result.confidence == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest tests/test_intent_router.py -v 2>&1 | tail -20
```
Expected: FAIL — `backend.intent_router` doesn't exist.

- [ ] **Step 3: Create `backend/intent_router.py`**

```python
# backend/intent_router.py
"""LLM-based intent router for the OSINT Atlas command console.

Classifies a user query into one of {aggregate, entity_narrative, action, smalltalk}
so the chat handler can dispatch to the right tool:

- aggregate       → SQL GROUP BY over doe_contracts.db (Task 4)
- entity_narrative → 4-lane HybridRetriever (Task 2)
- action          → existing MAP_CMD path (no change)
- smalltalk       → no retrieval, just chat
"""
from typing import Literal
from pydantic import BaseModel, Field

from backend.mercury_client import HermesClient


class IntentClassification(BaseModel):
    intent: Literal["aggregate", "entity_narrative", "action", "smalltalk"]
    confidence: float = Field(ge=0.0, le=1.0)
    search_terms: list[str] = Field(default_factory=list)
    filters: dict = Field(default_factory=dict)
    target_contractor: str | None = None


# Hand-written JSON Schema (strict-mode compatible — additionalProperties: False
# at every level, all properties in required).
INTENT_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["intent", "confidence", "search_terms", "filters", "target_contractor"],
    "properties": {
        "intent": {
            "type": "string",
            "enum": ["aggregate", "entity_narrative", "action", "smalltalk"],
            "description": (
                "aggregate: questions like 'who has contracts for X', 'how many contractors do Y', 'list all in state Z'. "
                "entity_narrative: questions about ONE specific contractor's posture, contracts, or details. "
                "action: 'show me X on the map', 'run kill chain on Y', 'open the panel for Z'. "
                "smalltalk: greetings, thanks, off-topic chat."
            ),
        },
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Your confidence (0-1) in the intent classification.",
        },
        "search_terms": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Key terms to search the contract database for. Extract topical terms, "
                "not stopwords. For 'who has contracts for radiation hardening', return "
                "['radiation hardening']. Empty list if no searchable terms (e.g., smalltalk)."
            ),
        },
        "filters": {
            "type": "object",
            "additionalProperties": False,
            "required": ["state", "fiscal_year", "min_obligation"],
            "properties": {
                "state": {"type": ["string", "null"], "description": "2-letter state code or full state name, or null"},
                "fiscal_year": {"type": ["integer", "null"], "description": "fiscal year (e.g. 2025), or null"},
                "min_obligation": {"type": ["number", "null"], "description": "minimum dollar threshold, or null"},
            },
        },
        "target_contractor": {
            "type": ["string", "null"],
            "description": (
                "If the user names a specific contractor (e.g. 'Honeywell', 'Lawrence Livermore'), "
                "return its name as a string. Otherwise null. Only set for entity_narrative intent."
            ),
        },
    },
}


_INTENT_SYSTEM_PROMPT = """\
You are an intent classifier for a contractor intelligence chat system. Your job is to \
classify the user's query into ONE of four intents and extract any search terms or filters.

INTENTS:
- aggregate: The user wants a list, count, or sum across MULTIPLE contractors. Examples:
  "who has contracts for cybersecurity", "how many contractors are in California",
  "list all DOE labs", "top contractors by obligation in 2025"
- entity_narrative: The user wants details about ONE specific contractor. Examples:
  "tell me about Lawrence Livermore", "what's Honeywell's cybersecurity posture",
  "show me Boeing's contracts"
- action: The user wants the system to DO something (visualize, analyze, run a workflow):
  "show this on the map", "run a kill chain on Honeywell", "filter to Texas"
- smalltalk: greetings, thanks, off-topic chat with no information request

Extract search_terms (the topical phrases the database should be searched for) and any \
explicit filters (state, fiscal_year, min_obligation). Set target_contractor only if the \
user names a specific contractor.

Return JSON matching the strict schema. Do not add fields. Use null for missing optionals.
"""


async def classify_intent(
    query: str,
    hermes: HermesClient,
    recent_history: list[dict] | None = None,
) -> IntentClassification:
    """Classify a query into one of 4 intents using Hermes-4-405B structured output.
    
    On any failure (network, malformed JSON, etc.), returns a safe default of
    intent='entity_narrative' with confidence 0.0 — this routes the query through
    the retrieval path, which is the most generally-useful fallback.
    """
    messages = [
        {"role": "system", "content": _INTENT_SYSTEM_PROMPT},
    ]
    if recent_history:
        # Include the last 2 turns for context resolution ("the second one" → ?)
        for msg in recent_history[-2:]:
            if msg.get("role") in ("user", "assistant"):
                messages.append({"role": msg["role"], "content": (msg.get("content") or "")[:500]})
    messages.append({"role": "user", "content": query})

    try:
        raw = await hermes.chat_structured(messages, INTENT_SCHEMA, max_tokens=500)
        return IntentClassification(**raw)
    except Exception as e:
        print(f"[intent_router] classification failed, defaulting to entity_narrative: {e}")
        return IntentClassification(
            intent="entity_narrative",
            confidence=0.0,
            search_terms=[],
            filters={},
            target_contractor=None,
        )
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
python3 -m pytest tests/test_intent_router.py -v 2>&1 | tail -20
```
Expected: `4 passed`.

- [ ] **Step 5: Wire `classify_intent` into `atlas_chat`**

In `test_atlas_server.py`, at the top of the `atlas_chat` function (right after the existing `system_content` initialization, around line 1092), add the intent classification call:

```python
    # ── Intent classification (Task 3) ──
    from backend.intent_router import classify_intent
    intent = await classify_intent(req.query, hermes, recent_history=req.messages)
```

Then update the existing retrieval block (added in Task 2) to ONLY fire when intent is `entity_narrative` or `aggregate`:

```python
    # ── Retrieval (Task 2, gated by intent in Task 3) ──
    retriever = get_retriever()
    retrieval_path = "legacy_substring"
    retrieval_results_count = 0
    retrieval_results_preview: list[str] = []

    if retriever is not None and intent.intent in ("entity_narrative", "aggregate"):
        try:
            # Use the LLM-extracted search terms if available, else the raw query
            search_query = " ".join(intent.search_terms) if intent.search_terms else req.query
            results = await asyncio.to_thread(retriever.search, search_query, 15, True)
            if results.contracts:
                contract_context = "\n".join(
                    f"- {c.recipient}: {c.description[:200]} (${c.obligation:,.0f})"
                    for c in results.contracts[:15]
                )
                system_content += (
                    "\n\nRELEVANT CONTRACT DATA (from 4-lane retrieval):\n"
                    + contract_context
                )
                retrieval_path = "hybrid_4lane"
                retrieval_results_count = len(results.contracts)
                retrieval_results_preview = [
                    f"{c.recipient}: {c.description[:80]}"
                    for c in results.contracts[:3]
                ]
        except Exception as e:
            print(f"[atlas-chat] retrieval failed mid-request, using legacy: {e}")
```

Then update the `_log_chat_turn` call to populate `intent_classification`:

```python
        _log_chat_turn({
            ...
            "intent_classification": intent.model_dump(),
            ...
        })
```

- [ ] **Step 6: Re-run all chat tests to confirm no regression**

```bash
python3 -m pytest tests/test_intent_router.py tests/test_atlas_chat_logging.py tests/test_atlas_chat_retrieval.py -v 2>&1 | tail -25
```

Expected: all pass. The retrieval test must be updated to mock `classify_intent` to return `intent="entity_narrative"` (otherwise the test query "tell me about Honeywell's cybersecurity" would route to the LLM which isn't mocked). Update `tests/test_atlas_chat_retrieval.py` to add this mock at the start of `fake_retriever_chat` fixture:

```python
    # Mock the intent router to skip the LLM call
    from backend.intent_router import IntentClassification
    async def fake_classify(query, hermes, recent_history=None):
        return IntentClassification(
            intent="entity_narrative",
            confidence=0.95,
            search_terms=["honeywell", "cybersecurity"],
            filters={},
            target_contractor="Honeywell",
        )
    monkeypatch.setattr("backend.intent_router.classify_intent", fake_classify)
```

Re-run the test to confirm it still passes.

- [ ] **Step 7: Commit**

```bash
git add backend/intent_router.py tests/test_intent_router.py test_atlas_server.py tests/test_atlas_chat_retrieval.py
git commit -m "feat: LLM-based intent router via Hermes structured output — Task 3"
```

---

## Task 4: SQL aggregator + dispatch from intent=aggregate

**Files:**
- Create: `backend/sql_aggregator.py`
- Create: `tests/test_sql_aggregator.py`
- Modify: `test_atlas_server.py` (dispatch from intent=aggregate)

**Ground Truth (verify before coding):**
- `doe_contracts.db` schema, table `contracts`, columns: `contract_transaction_unique_key, recipient_name, recipient_state_name, transaction_description, federal_action_obligation, action_date_fiscal_year, product_or_service_code_description, naics_description` (verified earlier in the conversation summary)
- 250,125 rows, 11,640 unique recipients
- Indexes exist on recipient_name, fiscal_year, agency_name
- Use `sqlite3.connect(...)` with `row_factory = sqlite3.Row` for dict-like row access
- Always parameterize the LIKE query (`?`) to prevent SQL injection — even though the search terms come from the LLM intent router, treat them as untrusted

**Provides:**
- `backend/sql_aggregator.py` exports:
  - `@dataclass class ContractorRollup` with fields `recipient_name, contract_count, total_obligation, fiscal_years, top_psc, top_naics, sample_descriptions`
  - `def aggregate_contracts(db_path: str, search_terms: list[str], filters: dict, limit: int = 20) -> list[ContractorRollup]`
- `intent=aggregate` queries now produce a `CONTRACTOR ROLLUPS` block in the prompt
- `retrieval_path == "sql_aggregate"` in chat log

**Requires:** Task 3 (intent router decides when to dispatch here)

**Integration test spec:** Pytest test using a temp sqlite file built with a known fixture (5 contracts across 3 recipients). Asserts `aggregate_contracts(["nuclear"], {})` returns the right rollup with correct counts and totals. Second test asserts that when filters={"state": "CA"} is set, only CA recipients are returned. Third test asserts SQL injection attempts in search_terms are escaped.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sql_aggregator.py
import os
import sqlite3
import tempfile
import pytest

from backend.sql_aggregator import aggregate_contracts, ContractorRollup


@pytest.fixture
def fixture_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE contracts (
            contract_transaction_unique_key TEXT PRIMARY KEY,
            recipient_name TEXT,
            recipient_state_name TEXT,
            transaction_description TEXT,
            federal_action_obligation REAL,
            action_date_fiscal_year INTEGER,
            product_or_service_code_description TEXT,
            naics_description TEXT
        )
    """)
    rows = [
        ("K1", "HONEYWELL FED MFG", "MO", "Nuclear waste cleanup project", 5_000_000, 2024, "R&D", "RESEARCH"),
        ("K2", "HONEYWELL FED MFG", "MO", "Nuclear materials handling", 3_000_000, 2025, "R&D", "RESEARCH"),
        ("K3", "LOCKHEED MARTIN", "CA", "Nuclear cleanup support", 8_000_000, 2024, "ENG", "ENGINEERING"),
        ("K4", "BOEING", "WA", "Aircraft maintenance", 1_000_000, 2024, "MFG", "MANUFACTURING"),
        ("K5", "LOCKHEED MARTIN", "CA", "Nuclear waste containment", 2_000_000, 2025, "ENG", "ENGINEERING"),
    ]
    conn.executemany("INSERT INTO contracts VALUES (?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    conn.close()
    yield path
    os.unlink(path)


def test_aggregate_basic_search(fixture_db):
    rollups = aggregate_contracts(fixture_db, ["nuclear"], {}, limit=10)
    assert len(rollups) == 2  # Honeywell + Lockheed (Boeing has no nuclear contracts)
    # Sorted by total_obligation DESC
    assert rollups[0].recipient_name == "LOCKHEED MARTIN"
    assert rollups[0].contract_count == 2
    assert rollups[0].total_obligation == 10_000_000
    assert rollups[1].recipient_name == "HONEYWELL FED MFG"
    assert rollups[1].contract_count == 2
    assert rollups[1].total_obligation == 8_000_000


def test_aggregate_with_state_filter(fixture_db):
    rollups = aggregate_contracts(fixture_db, ["nuclear"], {"state": "CA"}, limit=10)
    assert len(rollups) == 1
    assert rollups[0].recipient_name == "LOCKHEED MARTIN"


def test_aggregate_with_fiscal_year_filter(fixture_db):
    rollups = aggregate_contracts(fixture_db, ["nuclear"], {"fiscal_year": 2024}, limit=10)
    # Only the 2024 nuclear contracts: HONEYWELL K1 ($5M), LOCKHEED K3 ($8M)
    assert len(rollups) == 2
    by_name = {r.recipient_name: r for r in rollups}
    assert by_name["LOCKHEED MARTIN"].total_obligation == 8_000_000
    assert by_name["HONEYWELL FED MFG"].total_obligation == 5_000_000


def test_aggregate_sql_injection_safe(fixture_db):
    # Even with hostile input, the LIKE pattern should be parameterized
    malicious = ["x'; DROP TABLE contracts; --"]
    rollups = aggregate_contracts(fixture_db, malicious, {}, limit=10)
    # Should return zero rows, not crash, and the table should still exist
    assert rollups == []
    conn = sqlite3.connect(fixture_db)
    cnt = conn.execute("SELECT COUNT(*) FROM contracts").fetchone()[0]
    assert cnt == 5  # table not dropped
    conn.close()


def test_aggregate_returns_sample_descriptions(fixture_db):
    rollups = aggregate_contracts(fixture_db, ["nuclear"], {}, limit=10)
    lockheed = next(r for r in rollups if r.recipient_name == "LOCKHEED MARTIN")
    assert len(lockheed.sample_descriptions) >= 1
    assert any("Nuclear" in s for s in lockheed.sample_descriptions)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest tests/test_sql_aggregator.py -v 2>&1 | tail -20
```
Expected: FAIL — `backend.sql_aggregator` doesn't exist.

- [ ] **Step 3: Create `backend/sql_aggregator.py`**

```python
# backend/sql_aggregator.py
"""SQL aggregation path for intent=aggregate queries.

Vector RAG returns top-k chunks. SQL returns GROUP BY rollups. The user's
question 'who has contracts for nuclear waste' needs SUM(obligation) and
COUNT(*) over potentially hundreds of matching rows — vector retrieval can't
do that. This module is the aggregate path.
"""
import sqlite3
from dataclasses import dataclass, field


@dataclass
class ContractorRollup:
    recipient_name: str
    contract_count: int
    total_obligation: float
    fiscal_years: list[int] = field(default_factory=list)
    top_psc: list[str] = field(default_factory=list)
    top_naics: list[str] = field(default_factory=list)
    sample_descriptions: list[str] = field(default_factory=list)


def aggregate_contracts(
    db_path: str,
    search_terms: list[str],
    filters: dict,
    limit: int = 20,
) -> list[ContractorRollup]:
    """GROUP BY recipient_name aggregation matching search_terms + filters.

    Args:
        db_path: path to doe_contracts.db
        search_terms: list of terms to LIKE-match against description, PSC, NAICS
        filters: optional {"state": str, "fiscal_year": int, "min_obligation": float}
        limit: max number of rollups to return (default 20)

    Returns:
        List of ContractorRollup, sorted by total_obligation DESC.
        Empty list if no matches.
    """
    if not search_terms:
        return []

    where_parts: list[str] = []
    params: list = []

    # Search terms: each term must match in description, PSC, or NAICS
    # All terms ANDed (e.g., "nuclear waste" requires both nuclear AND waste)
    for term in search_terms:
        where_parts.append(
            "(transaction_description LIKE ? "
            "OR product_or_service_code_description LIKE ? "
            "OR naics_description LIKE ?)"
        )
        wildcard = f"%{term}%"
        params.extend([wildcard, wildcard, wildcard])

    # Filters
    if filters.get("state"):
        where_parts.append("recipient_state_name = ?")
        params.append(filters["state"])
    if filters.get("fiscal_year"):
        where_parts.append("action_date_fiscal_year = ?")
        params.append(filters["fiscal_year"])
    if filters.get("min_obligation"):
        where_parts.append("federal_action_obligation >= ?")
        params.append(filters["min_obligation"])

    where_clause = " AND ".join(where_parts) if where_parts else "1=1"

    sql = f"""
        SELECT
            recipient_name,
            COUNT(*) as contract_count,
            SUM(federal_action_obligation) as total_obligation,
            GROUP_CONCAT(DISTINCT action_date_fiscal_year) as years,
            GROUP_CONCAT(DISTINCT product_or_service_code_description) as pscs,
            GROUP_CONCAT(DISTINCT naics_description) as naics_list
        FROM contracts
        WHERE {where_clause}
            AND recipient_name IS NOT NULL
            AND federal_action_obligation IS NOT NULL
        GROUP BY recipient_name
        ORDER BY total_obligation DESC
        LIMIT ?
    """
    params.append(limit)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(sql, params).fetchall()

    # Fetch sample descriptions per recipient (3 each) — separate query to keep
    # the GROUP BY clean
    rollups: list[ContractorRollup] = []
    for row in rows:
        sample_sql = f"""
            SELECT transaction_description
            FROM contracts
            WHERE recipient_name = ? AND ({where_clause})
            ORDER BY federal_action_obligation DESC
            LIMIT 3
        """
        sample_params = [row["recipient_name"]] + params[:-1]  # exclude limit
        samples = conn.execute(sample_sql, sample_params).fetchall()

        rollups.append(ContractorRollup(
            recipient_name=row["recipient_name"],
            contract_count=row["contract_count"],
            total_obligation=row["total_obligation"] or 0.0,
            fiscal_years=sorted(int(y) for y in (row["years"] or "").split(",") if y),
            top_psc=[p for p in (row["pscs"] or "").split(",")[:3] if p],
            top_naics=[n for n in (row["naics_list"] or "").split(",")[:3] if n],
            sample_descriptions=[s["transaction_description"] for s in samples if s["transaction_description"]],
        ))

    conn.close()
    return rollups
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
python3 -m pytest tests/test_sql_aggregator.py -v 2>&1 | tail -25
```
Expected: `5 passed`.

- [ ] **Step 5: Dispatch from intent=aggregate in atlas_chat**

In `test_atlas_server.py`, modify the retrieval block (added in Tasks 2/3) to handle the aggregate intent BEFORE the entity_narrative path:

```python
    # ── Retrieval (Task 2, gated by intent in Task 3, aggregated in Task 4) ──
    retriever = get_retriever()
    retrieval_path = "legacy_substring"
    retrieval_results_count = 0
    retrieval_results_preview: list[str] = []

    if intent.intent == "aggregate" and intent.search_terms:
        try:
            from backend.sql_aggregator import aggregate_contracts
            rollups = await asyncio.to_thread(
                aggregate_contracts,
                str(BASE / "doe_contracts.db"),
                intent.search_terms,
                intent.filters or {},
                20,
            )
            if rollups:
                rollup_lines = []
                for r in rollups:
                    years_str = ",".join(str(y) for y in r.fiscal_years[:5])
                    rollup_lines.append(
                        f"- {r.recipient_name}: {r.contract_count} contracts, "
                        f"${r.total_obligation:,.0f} total (FY {years_str}) | "
                        f"PSC: {'; '.join(r.top_psc[:2])}"
                    )
                system_content += (
                    "\n\nCONTRACTOR ROLLUPS (matching your aggregate query — "
                    "sorted by total obligation):\n"
                    + "\n".join(rollup_lines)
                    + "\n\nWhen presenting these to the user, list them as a "
                      "ranked table or bullet list. Cite the dollar amounts and "
                      "contract counts directly from this data."
                )
                retrieval_path = "sql_aggregate"
                retrieval_results_count = len(rollups)
                retrieval_results_preview = [
                    f"{r.recipient_name}: {r.contract_count} contracts, ${r.total_obligation:,.0f}"
                    for r in rollups[:3]
                ]
        except Exception as e:
            print(f"[atlas-chat] SQL aggregation failed: {e}")

    elif retriever is not None and intent.intent in ("entity_narrative",):
        try:
            search_query = " ".join(intent.search_terms) if intent.search_terms else req.query
            results = await asyncio.to_thread(retriever.search, search_query, 15, True)
            if results.contracts:
                contract_context = "\n".join(
                    f"- {c.recipient}: {c.description[:200]} (${c.obligation:,.0f})"
                    for c in results.contracts[:15]
                )
                system_content += (
                    "\n\nRELEVANT CONTRACT DATA (from 4-lane retrieval):\n"
                    + contract_context
                )
                retrieval_path = "hybrid_4lane"
                retrieval_results_count = len(results.contracts)
                retrieval_results_preview = [
                    f"{c.recipient}: {c.description[:80]}"
                    for c in results.contracts[:3]
                ]
        except Exception as e:
            print(f"[atlas-chat] retrieval failed: {e}")
```

- [ ] **Step 6: Add an end-to-end test for the aggregate path**

```python
# Append to tests/test_atlas_chat_retrieval.py

@pytest.fixture
def fake_aggregate_chat(tmp_path, monkeypatch):
    import test_atlas_server as srv
    from backend.intent_router import IntentClassification
    from backend.sql_aggregator import ContractorRollup

    monkeypatch.setattr(srv, "_ATLAS_CHAT_LOG", tmp_path / "atlas_chat.jsonl")
    srv.SITE_PASSWORD = ""

    async def fake_classify(query, hermes, recent_history=None):
        return IntentClassification(
            intent="aggregate",
            confidence=0.95,
            search_terms=["nuclear waste"],
            filters={},
            target_contractor=None,
        )
    monkeypatch.setattr("backend.intent_router.classify_intent", fake_classify)

    fake_rollups = [
        ContractorRollup(recipient_name="HONEYWELL FED MFG", contract_count=12,
                         total_obligation=50_000_000, fiscal_years=[2024, 2025],
                         top_psc=["R&D"], top_naics=["RESEARCH"],
                         sample_descriptions=["Nuclear waste cleanup"]),
        ContractorRollup(recipient_name="LOCKHEED MARTIN", contract_count=8,
                         total_obligation=30_000_000, fiscal_years=[2024],
                         top_psc=["ENG"], top_naics=["ENGINEERING"],
                         sample_descriptions=["Nuclear cleanup support"]),
    ]
    def fake_agg(db_path, terms, filters, limit=20):
        return fake_rollups
    monkeypatch.setattr("backend.sql_aggregator.aggregate_contracts", fake_agg)

    async def fake_stream(messages, *args, **kwargs):
        for tok in ["Honeywell", " has", " 12 contracts"]:
            yield tok
    monkeypatch.setattr(srv.hermes, "is_available", lambda: True)
    monkeypatch.setattr(srv.hermes, "chat_stream", fake_stream)
    return tmp_path / "atlas_chat.jsonl"


@pytest.mark.asyncio
async def test_chat_aggregate_path_injects_rollups(fake_aggregate_chat):
    import test_atlas_server as srv
    payload = {"query": "who has contracts for nuclear waste",
               "session_id": "s2", "messages": [], "contractor_count": 2214, "data_context": ""}

    transport = ASGITransport(app=srv.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/atlas-chat", json=payload)
        assert resp.status_code == 200
        _ = resp.text

    record = json.loads(fake_aggregate_chat.read_text().strip().splitlines()[-1])
    assert record["retrieval_path"] == "sql_aggregate"
    assert record["retrieval_results_count"] == 2

    system_msg = record["full_messages"][0]
    assert "CONTRACTOR ROLLUPS" in system_msg["content"]
    assert "HONEYWELL FED MFG" in system_msg["content"]
    assert "12 contracts" in system_msg["content"]
    assert "$50,000,000" in system_msg["content"]
```

- [ ] **Step 7: Run all chat tests + sql aggregator tests**

```bash
python3 -m pytest tests/test_intent_router.py tests/test_sql_aggregator.py tests/test_atlas_chat_logging.py tests/test_atlas_chat_retrieval.py -v 2>&1 | tail -30
```
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add backend/sql_aggregator.py tests/test_sql_aggregator.py test_atlas_server.py tests/test_atlas_chat_retrieval.py
git commit -m "feat: SQL aggregator for intent=aggregate queries — Task 4"
```

---

## Task 5: Token-budgeted history

**Files:**
- Create: `backend/history_budget.py`
- Create: `tests/test_history_budget.py`
- Modify: `test_atlas_server.py` (replace lines 1100-1102)

**Ground Truth (verify before coding):**
- Current cap: `test_atlas_server.py:1100`: `history = list(req.messages[-6:])`
- Per-message truncation: `test_atlas_server.py:1107`: `(msg.get("content") or "")[:500]`
- Token estimation heuristic: `len(content) // 4 + 10` per message (good enough; we're aiming for under-fill, not exact count)

**Provides:**
- `backend/history_budget.py` exports `def budget_history(messages: list[dict], target_tokens: int = 8000) -> list[dict]`
- The 6-turn cap is replaced; per-message 500-char truncation is removed

**Requires:** Task 0 (the chat log will record the new history token estimate)

**Integration test spec:** Pytest test that creates 30 fake messages of varying lengths and asserts `budget_history(messages, 8000)` returns the correct subset (most recent N that fit) with the original content unchanged.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_history_budget.py
from backend.history_budget import budget_history


def test_budget_returns_all_when_under_budget():
    messages = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]
    out = budget_history(messages, target_tokens=1000)
    assert out == messages


def test_budget_drops_oldest_when_over():
    # 30 messages × ~100 chars each = ~750 tokens. Budget 200 → should keep ~6.
    messages = [
        {"role": "user" if i % 2 == 0 else "assistant",
         "content": f"This is message number {i:03d} " * 4}  # ~100 chars
        for i in range(30)
    ]
    out = budget_history(messages, target_tokens=200)
    assert len(out) < len(messages)
    assert len(out) > 0
    # Most recent message must always be included
    assert out[-1] == messages[-1]
    # Order must be preserved (oldest dropped, not interleaved)
    for i in range(len(out) - 1):
        original_idx = messages.index(out[i])
        next_idx = messages.index(out[i + 1])
        assert next_idx == original_idx + 1


def test_budget_preserves_content_unchanged():
    """Message content must NOT be truncated by budget_history."""
    long_msg = {"role": "user", "content": "x" * 5000}
    out = budget_history([long_msg], target_tokens=10000)
    assert out[0]["content"] == "x" * 5000


def test_budget_handles_empty_messages():
    assert budget_history([], target_tokens=1000) == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest tests/test_history_budget.py -v 2>&1 | tail -15
```
Expected: FAIL — `backend.history_budget` doesn't exist.

- [ ] **Step 3: Create `backend/history_budget.py`**

```python
# backend/history_budget.py
"""Token-budgeted conversation history.

Replaces the legacy 6-turn / 500-char cap with a budget that keeps the most
recent messages whose total estimated tokens fit under target_tokens.

Token estimation is intentionally rough — we use len(content) // 4 + 10 per
message, which slightly overestimates for English (good — we want to under-fill
rather than overflow).
"""


def _est_tokens(msg: dict) -> int:
    content = msg.get("content", "") or ""
    return len(content) // 4 + 10


def budget_history(messages: list[dict], target_tokens: int = 8000) -> list[dict]:
    """Return the longest tail of `messages` whose total tokens fit under target.

    Walks backwards from the newest message, including each one until adding
    the next would exceed target_tokens. The returned list preserves the
    original message order (oldest of the kept slice first).

    Args:
        messages: list of {"role": ..., "content": ...} dicts
        target_tokens: budget in estimated tokens (default 8000)

    Returns:
        Subset of messages, in original order, with content UNCHANGED.
    """
    if not messages:
        return []

    kept_reversed: list[dict] = []
    used = 0
    for msg in reversed(messages):
        est = _est_tokens(msg)
        if kept_reversed and used + est > target_tokens:
            break
        kept_reversed.append(msg)
        used += est

    return list(reversed(kept_reversed))
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
python3 -m pytest tests/test_history_budget.py -v 2>&1 | tail -15
```
Expected: `4 passed`.

- [ ] **Step 5: Replace the 6-turn cap in `atlas_chat`**

In `test_atlas_server.py`, replace lines 1100-1108 (the current history-building block):

```python
    # ── Token-budgeted history (Task 5, replaces the 6-turn / 500-char cap) ──
    from backend.history_budget import budget_history
    history_msgs = budget_history(req.messages, target_tokens=8000)
    if history_msgs and history_msgs[-1].get("role") == "user" and history_msgs[-1].get("content") == req.query:
        history_msgs = history_msgs[:-1]

    messages = [{"role": "system", "content": system_content}]
    for msg in history_msgs:
        if msg.get("role") in ("user", "assistant"):
            messages.append({"role": msg["role"], "content": msg.get("content") or ""})
    messages.append({"role": "user", "content": req.query})
```

- [ ] **Step 6: Run all chat tests to confirm no regression**

```bash
python3 -m pytest tests/test_history_budget.py tests/test_atlas_chat_logging.py tests/test_atlas_chat_retrieval.py tests/test_intent_router.py tests/test_sql_aggregator.py -v 2>&1 | tail -30
```
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add backend/history_budget.py tests/test_history_budget.py test_atlas_server.py
git commit -m "feat: token-budgeted history replaces 6-turn cap — Task 5"
```

---

## Task 6: Server-side ConversationState + frontend session_id

**Files:**
- Create: `backend/conversation_state.py`
- Create: `tests/test_conversation_state.py`
- Modify: `test_atlas_server.py` (use ConversationStore as authoritative history)
- Modify: `frontend/static/contractor-map.html` (lift telemetry session_id, send in chat payload)

**Ground Truth (verify before coding):**
- The frontend telemetry IIFE generates `crypto.randomUUID()` for session_id (added in the previous robustness commit cluster). It currently lives inside the `setupErrorTelemetry` IIFE — Task 6 needs to lift it to module scope.
- The chat payload-building code is at `frontend/static/contractor-map.html:6076-6081`:
  ```javascript
  const payload = {
    query: query,
    messages: atlasChatMessages.slice(-10),
    contractor_count: DATA ? DATA.contractors.length : 0,
    data_context: dataContext + sessionContext,
  };
  ```
- Verify the existing telemetry IIFE location (search for `setupErrorTelemetry` in contractor-map.html)
- `time.time()` returns a float; use it for timestamps
- The chat handler currently uses `req.messages` as the history source — Task 6 will prefer `ConversationStore` state when present and fall back to `req.messages`

**Provides:**
- `backend/conversation_state.py` exports:
  - `@dataclass class ConversationState` with fields `session_id, verbatim_turns, rolling_summary, entity_tracker, created_at, last_used_at, turn_count`
  - `class ConversationStore` with methods `get_or_create(session_id) -> ConversationState`, `append_turn(session_id, role, content)`, `evict_expired()`
- Frontend: `ATLAS_SESSION_ID` lifted to module scope, sent in chat payload

**Requires:** Task 5 (history budget — ConversationStore now feeds budget_history)

**Integration test spec:** Pytest test that creates a ConversationStore with TTL=1s, max_sessions=3. Creates 3 sessions, asserts each has its own state. Sleeps 1.1s, calls evict_expired, asserts all 3 evicted. Creates 4 sessions with no TTL, asserts oldest is evicted. Round-trips messages: append a turn, retrieve via get_or_create, assert it's there.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_conversation_state.py
import time
import pytest

from backend.conversation_state import ConversationState, ConversationStore


def test_conversation_store_round_trips_turns():
    store = ConversationStore()
    store.append_turn("s1", "user", "hello")
    store.append_turn("s1", "assistant", "hi there")
    state = store.get_or_create("s1")
    assert state.session_id == "s1"
    assert len(state.verbatim_turns) == 2
    assert state.verbatim_turns[0]["role"] == "user"
    assert state.verbatim_turns[0]["content"] == "hello"
    assert state.verbatim_turns[1]["content"] == "hi there"
    assert state.turn_count == 2


def test_conversation_store_isolates_sessions():
    store = ConversationStore()
    store.append_turn("s1", "user", "alpha")
    store.append_turn("s2", "user", "beta")
    s1 = store.get_or_create("s1")
    s2 = store.get_or_create("s2")
    assert s1.verbatim_turns[0]["content"] == "alpha"
    assert s2.verbatim_turns[0]["content"] == "beta"


def test_conversation_store_ttl_eviction():
    store = ConversationStore(ttl_seconds=0.1)
    store.append_turn("s1", "user", "hello")
    assert "s1" in store._sessions
    time.sleep(0.15)
    store.evict_expired()
    assert "s1" not in store._sessions


def test_conversation_store_max_sessions_eviction():
    store = ConversationStore(max_sessions=2)
    store.append_turn("s1", "user", "a")
    time.sleep(0.01)
    store.append_turn("s2", "user", "b")
    time.sleep(0.01)
    store.append_turn("s3", "user", "c")  # should evict s1 (oldest)
    assert "s1" not in store._sessions
    assert "s2" in store._sessions
    assert "s3" in store._sessions


def test_get_or_create_resets_last_used():
    store = ConversationStore()
    store.append_turn("s1", "user", "hi")
    t0 = store._sessions["s1"].last_used_at
    time.sleep(0.05)
    store.get_or_create("s1")
    assert store._sessions["s1"].last_used_at > t0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest tests/test_conversation_state.py -v 2>&1 | tail -20
```
Expected: FAIL — `backend.conversation_state` doesn't exist.

- [ ] **Step 3: Create `backend/conversation_state.py`**

```python
# backend/conversation_state.py
"""Server-side conversation state for the OSINT Atlas command console.

Replaces the stateless 'frontend sends history every turn' pattern with a
session-keyed in-memory store. Foundation for rolling summaries (Task 7) and
entity tracking (Task 7).

Bounds:
- max_sessions: cap on total sessions (default 200, evict oldest when exceeded)
- ttl_seconds: idle timeout (default 3600, evict on get_or_create)

For a single-process Railway dyno this is fine. If we ever scale horizontally,
swap to redis or per-row sqlite.
"""
import time
from dataclasses import dataclass, field


@dataclass
class ConversationState:
    session_id: str
    verbatim_turns: list[dict] = field(default_factory=list)
    rolling_summary: str = ""           # filled by Task 7
    entity_tracker: list[str] = field(default_factory=list)  # filled by Task 7
    created_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)
    turn_count: int = 0


class ConversationStore:
    def __init__(self, max_sessions: int = 200, ttl_seconds: float = 3600.0):
        self._sessions: dict[str, ConversationState] = {}
        self._max = max_sessions
        self._ttl = ttl_seconds

    def evict_expired(self) -> None:
        now = time.time()
        expired = [
            sid for sid, st in self._sessions.items()
            if now - st.last_used_at > self._ttl
        ]
        for sid in expired:
            del self._sessions[sid]

    def _evict_oldest_if_full(self) -> None:
        while len(self._sessions) >= self._max:
            oldest_sid = min(
                self._sessions.keys(),
                key=lambda k: self._sessions[k].last_used_at,
            )
            del self._sessions[oldest_sid]

    def get_or_create(self, session_id: str) -> ConversationState:
        self.evict_expired()
        if session_id not in self._sessions:
            self._evict_oldest_if_full()
            self._sessions[session_id] = ConversationState(session_id=session_id)
        else:
            self._sessions[session_id].last_used_at = time.time()
        return self._sessions[session_id]

    def append_turn(self, session_id: str, role: str, content: str) -> None:
        state = self.get_or_create(session_id)
        state.verbatim_turns.append({"role": role, "content": content})
        state.turn_count += 1
        state.last_used_at = time.time()
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
python3 -m pytest tests/test_conversation_state.py -v 2>&1 | tail -20
```
Expected: `5 passed`.

- [ ] **Step 5: Wire ConversationStore into atlas_chat**

In `test_atlas_server.py`, after the retriever singleton (added in Task 2), add:

```python
# ── Conversation state (Task 6) ──
from backend.conversation_state import ConversationStore
_conversation_store = ConversationStore(max_sessions=200, ttl_seconds=3600.0)
```

Then modify the history-building block (currently uses `req.messages`):

```python
    # ── Token-budgeted history (Task 5) sourced from ConversationStore (Task 6) ──
    from backend.history_budget import budget_history

    # Prefer server-side state when session_id is provided; fall back to client-supplied
    # messages on first request after a server restart (state would be empty).
    if req.session_id:
        state = _conversation_store.get_or_create(req.session_id)
        if state.verbatim_turns:
            source_messages = state.verbatim_turns
        else:
            source_messages = req.messages
    else:
        source_messages = req.messages

    history_msgs = budget_history(source_messages, target_tokens=8000)
    if history_msgs and history_msgs[-1].get("role") == "user" and history_msgs[-1].get("content") == req.query:
        history_msgs = history_msgs[:-1]
```

After the stream completes (inside `stream()`, after `accumulated_response.append(final_text)`), append both the user turn and the assistant turn to the ConversationStore:

```python
            # Persist to ConversationStore (Task 6) so the next turn has full state
            if req.session_id:
                _conversation_store.append_turn(req.session_id, "user", req.query)
                _conversation_store.append_turn(req.session_id, "assistant", final_text)
```

- [ ] **Step 6: Lift session_id to module scope in the frontend**

In `frontend/static/contractor-map.html`, find the `setupErrorTelemetry` IIFE (search for `setupErrorTelemetry`). It should contain something like `const SESSION_ID = crypto.randomUUID?.() || String(Date.now());`. 

Add this BEFORE the IIFE so the constant is in module scope:

```javascript
// Module-scoped session id, shared between telemetry (Task 5 of robustness plan)
// and chat (Task 6 of RAG plan). Generated once per page load.
const ATLAS_SESSION_ID = (typeof crypto !== 'undefined' && crypto.randomUUID)
  ? crypto.randomUUID()
  : 'sess_' + Date.now() + '_' + Math.random().toString(36).slice(2);
```

Then update the existing telemetry IIFE to use `ATLAS_SESSION_ID` instead of its local `SESSION_ID` (find and replace `SESSION_ID` with `ATLAS_SESSION_ID` inside that IIFE only).

- [ ] **Step 7: Send session_id in the chat payload**

In `frontend/static/contractor-map.html` around line 6076-6081, update the payload:

```javascript
const payload = {
    query: query,
    messages: atlasChatMessages.slice(-10),
    contractor_count: DATA ? DATA.contractors.length : 0,
    data_context: dataContext + sessionContext,
    session_id: ATLAS_SESSION_ID,
};
```

- [ ] **Step 8: Run all tests to verify no regression**

```bash
python3 -m pytest tests/test_conversation_state.py tests/test_atlas_chat_logging.py tests/test_atlas_chat_retrieval.py tests/test_history_budget.py -v 2>&1 | tail -30
python3 -m pytest tests/test_atlas_browser_compat.py --browser chromium -v 2>&1 | tail -10
```
Expected: all pass.

- [ ] **Step 9: Commit**

```bash
git add backend/conversation_state.py tests/test_conversation_state.py test_atlas_server.py frontend/static/contractor-map.html
git commit -m "feat: server-side ConversationState + frontend session_id wiring — Task 6"
```

---

## Task 7: Rolling summary + entity tracker (bundled)

**Files:**
- Modify: `backend/conversation_state.py` (add summary regeneration + entity extraction)
- Modify: `test_atlas_server.py` (call new methods, inject summary + tracker into prompt)
- Modify: `tests/test_conversation_state.py` (add tests for summary + tracker)

**Ground Truth (verify before coding):**
- `HermesClient.chat(messages, max_tokens)` (non-streaming) is at `backend/mercury_client.py:27-45`. Use it for the summary call.
- Loading contractor names: `frontend/static/contractors.json` is the source of truth (43 MB). Loading it into Python for entity extraction is fine — it's done once at module init. Path: `BASE / "frontend" / "static" / "contractors.json"`
- Contractor JSON shape: `{"contractors": [{"name": "HONEYWELL...", ...}, ...]}` — extract just the `name` field
- Entity matching: simple `name.lower() in text.lower()` over 2,214 names ≈ 5-10ms per message — good enough
- The summary is regenerated only when verbatim history would exceed the token budget (8K), not every turn

**Provides:**
- `ConversationState` now uses `rolling_summary` and `entity_tracker` fields meaningfully
- `ConversationStore.maybe_summarize(session_id, hermes, target_tokens)` async method
- Module-level `_load_contractor_names() -> list[str]` and `_extract_entities(text, names) -> list[str]` helpers
- `ConversationStore.update_entities(session_id, role, content, names)` method
- atlas_chat injects `PRIOR DISCUSSION SUMMARY:` and `USER IS CURRENTLY INVESTIGATING:` blocks into the system prompt

**Requires:** Task 6 (ConversationState exists)

**Integration test spec:** 
1. Pytest test that creates a ConversationStore, appends 30 long turns to one session, calls `maybe_summarize` with a mocked hermes that returns "fake summary text", asserts that `rolling_summary` is set and `verbatim_turns` is trimmed.
2. Pytest test that calls `update_entities` after a message mentioning "Honeywell" and "Lockheed", asserts both names are in `entity_tracker`.
3. Pytest test that verifies entity ordering by recency and dedup.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_conversation_state.py`:

```python
import asyncio
from unittest.mock import AsyncMock, MagicMock


def test_extract_entities_finds_known_names():
    from backend.conversation_state import _extract_entities
    names = ["HONEYWELL FED MFG", "LOCKHEED MARTIN", "BOEING"]
    text = "I want to know about Honeywell and lockheed martin."
    found = _extract_entities(text, names)
    assert "HONEYWELL FED MFG" in found
    assert "LOCKHEED MARTIN" in found
    assert "BOEING" not in found


def test_update_entities_dedupes_and_orders_by_recency():
    store = ConversationStore()
    names = ["HONEYWELL", "LOCKHEED", "BOEING"]
    store.update_entities("s1", "user", "tell me about Honeywell", names)
    store.update_entities("s1", "user", "now lockheed", names)
    store.update_entities("s1", "user", "back to honeywell", names)
    state = store.get_or_create("s1")
    # Honeywell should be most recent (re-mentioned), Lockheed before
    assert state.entity_tracker[-1] == "HONEYWELL"
    assert "LOCKHEED" in state.entity_tracker
    # Each name appears at most once
    assert len(state.entity_tracker) == len(set(state.entity_tracker))


@pytest.mark.asyncio
async def test_maybe_summarize_triggers_above_budget():
    store = ConversationStore()
    # 30 turns × ~500 chars = ~3700 tokens — under default 8K budget, won't trigger
    # 30 turns × ~2000 chars = ~15000 tokens — over default 8K, should trigger
    long_content = "x" * 2000
    for i in range(30):
        store.append_turn("s1", "user" if i % 2 == 0 else "assistant", long_content)

    fake_hermes = MagicMock()
    fake_hermes.chat = AsyncMock(return_value="The user has been discussing X, Y, Z.")
    fake_hermes.is_available = lambda: True

    summarized = await store.maybe_summarize("s1", fake_hermes, target_tokens=8000)
    assert summarized is True

    state = store.get_or_create("s1")
    assert state.rolling_summary == "The user has been discussing X, Y, Z."
    # Older verbatim turns should be trimmed (we keep only the tail that fits)
    assert len(state.verbatim_turns) < 30


@pytest.mark.asyncio
async def test_maybe_summarize_skips_when_under_budget():
    store = ConversationStore()
    store.append_turn("s1", "user", "short")
    store.append_turn("s1", "assistant", "short")
    fake_hermes = MagicMock()
    fake_hermes.chat = AsyncMock()
    summarized = await store.maybe_summarize("s1", fake_hermes, target_tokens=8000)
    assert summarized is False
    fake_hermes.chat.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_conversation_state.py -v 2>&1 | tail -25
```
Expected: 4 new tests FAIL — methods don't exist yet. Existing 5 tests still pass.

- [ ] **Step 3: Add entity extraction + summary methods to `backend/conversation_state.py`**

Append to the existing module:

```python
import json
import pathlib

from backend.history_budget import _est_tokens
from backend.mercury_client import HermesClient


_CONTRACTOR_NAMES_CACHE: list[str] | None = None


def _load_contractor_names(json_path: pathlib.Path | str | None = None) -> list[str]:
    """Load contractor names from contractors.json (cached after first call)."""
    global _CONTRACTOR_NAMES_CACHE
    if _CONTRACTOR_NAMES_CACHE is not None:
        return _CONTRACTOR_NAMES_CACHE
    if json_path is None:
        # Default location relative to repo root
        json_path = pathlib.Path(__file__).parent.parent / "frontend" / "static" / "contractors.json"
    try:
        with open(json_path) as f:
            data = json.load(f)
        names = [c.get("name", "") for c in data.get("contractors", []) if c.get("name")]
        _CONTRACTOR_NAMES_CACHE = sorted(set(names), key=len, reverse=True)  # longest first
        return _CONTRACTOR_NAMES_CACHE
    except Exception:
        _CONTRACTOR_NAMES_CACHE = []
        return _CONTRACTOR_NAMES_CACHE


def _extract_entities(text: str, names: list[str]) -> list[str]:
    """Find contractor names mentioned in the text. Case-insensitive substring match.
    
    Uses substring not full token match because contractors are often referenced by
    a partial name (e.g. 'Honeywell' for 'HONEYWELL FEDERAL MFG & TECH').
    """
    text_lower = text.lower()
    found = []
    for name in names:
        # Match either the full name OR the first word (e.g. "honeywell" matches "honeywell federal mfg")
        if name.lower() in text_lower:
            found.append(name)
            continue
        first_word = name.split()[0] if name.split() else ""
        if len(first_word) > 4 and first_word.lower() in text_lower:
            found.append(name)
    return found


_SUMMARIZE_PROMPT = """\
You are summarizing a chat conversation between a user and an OSINT analyst about \
DOE contractors. Distill the conversation into a 150-word "PRIOR DISCUSSION SUMMARY" \
that captures: which contractors were discussed, what specific topics or angles the \
user cared about, and any decisions or conclusions reached. Be specific — name \
contractors by name, mention concrete topics. Do NOT add commentary, do NOT speculate \
about unmentioned details, do NOT exceed 150 words.\
"""


# Extend the ConversationStore class with new methods
def _extend_conversation_store():
    async def maybe_summarize(
        self, session_id: str, hermes: HermesClient,
        target_tokens: int = 8000,
    ) -> bool:
        """If verbatim history exceeds target_tokens, regenerate the rolling summary
        and trim the oldest verbatim turns.
        
        Returns True if a summary was regenerated, False otherwise.
        """
        state = self.get_or_create(session_id)
        total = sum(_est_tokens(m) for m in state.verbatim_turns)
        if total <= target_tokens:
            return False
        if not hermes.is_available() if hasattr(hermes, "is_available") else False:
            return False

        # Summarize the OLDEST 70% of turns; keep the newest 30% verbatim
        cutoff = max(1, int(len(state.verbatim_turns) * 0.7))
        to_summarize = state.verbatim_turns[:cutoff]
        to_keep = state.verbatim_turns[cutoff:]

        transcript = "\n".join(
            f"{m.get('role', '?').upper()}: {m.get('content', '')[:1000]}"
            for m in to_summarize
        )
        if state.rolling_summary:
            transcript = f"PRIOR SUMMARY:\n{state.rolling_summary}\n\nNEW TURNS:\n{transcript}"

        try:
            messages = [
                {"role": "system", "content": _SUMMARIZE_PROMPT},
                {"role": "user", "content": transcript},
            ]
            summary = await hermes.chat(messages, max_tokens=300)
            state.rolling_summary = summary.strip()
            state.verbatim_turns = to_keep
            return True
        except Exception as e:
            print(f"[conversation_state] summary regeneration failed: {e}")
            return False

    def update_entities(self, session_id: str, role: str, content: str, names: list[str]) -> None:
        state = self.get_or_create(session_id)
        found = _extract_entities(content, names)
        for name in found:
            if name in state.entity_tracker:
                state.entity_tracker.remove(name)
            state.entity_tracker.append(name)
        # Cap at 10 most recent
        state.entity_tracker = state.entity_tracker[-10:]

    ConversationStore.maybe_summarize = maybe_summarize
    ConversationStore.update_entities = update_entities


_extend_conversation_store()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_conversation_state.py -v 2>&1 | tail -25
```
Expected: 9 passed (5 from Task 6 + 4 new).

- [ ] **Step 5: Wire summary + entity tracker into atlas_chat**

In `test_atlas_server.py`, in the `atlas_chat` function — after `_conversation_store.get_or_create(req.session_id)` (added in Task 6) — call the new methods:

```python
    # ── Memory layer (Task 7) ──
    if req.session_id:
        # Update entity tracker with the user's query (assistant response is added after stream)
        from backend.conversation_state import _load_contractor_names
        contractor_names = _load_contractor_names()
        _conversation_store.update_entities(req.session_id, "user", req.query, contractor_names)

        # Maybe summarize older turns (only fires if budget exceeded)
        await _conversation_store.maybe_summarize(req.session_id, hermes, target_tokens=8000)

        # Build the prompt augmentation from state
        state = _conversation_store.get_or_create(req.session_id)
        if state.rolling_summary:
            system_content += f"\n\nPRIOR DISCUSSION SUMMARY:\n{state.rolling_summary}"
        if state.entity_tracker:
            system_content += f"\n\nUSER IS CURRENTLY INVESTIGATING: {', '.join(state.entity_tracker[-10:])}"
```

After the stream completes (where Task 6 calls `append_turn`), also update entities for the assistant response:

```python
            if req.session_id:
                _conversation_store.append_turn(req.session_id, "user", req.query)
                _conversation_store.append_turn(req.session_id, "assistant", final_text)
                # Update entities from the assistant's response too
                from backend.conversation_state import _load_contractor_names
                _conversation_store.update_entities(req.session_id, "assistant", final_text, _load_contractor_names())
```

- [ ] **Step 6: Run all tests to confirm no regression**

```bash
python3 -m pytest tests/test_conversation_state.py tests/test_history_budget.py tests/test_atlas_chat_logging.py tests/test_atlas_chat_retrieval.py tests/test_intent_router.py tests/test_sql_aggregator.py -v 2>&1 | tail -40
python3 -m pytest tests/test_atlas_browser_compat.py --browser chromium -v 2>&1 | tail -10
```
Expected: all pass.

- [ ] **Step 7: Manual end-to-end check**

Start the server and walk through a real multi-turn conversation:

```bash
SITE_PASSWORD='' PORT=8765 python3 test_atlas_server.py &
SERVER_PID=$!
sleep 2
# Turn 1
curl -s -X POST http://localhost:8765/api/atlas-chat \
    -H "Content-Type: application/json" \
    -d '{"query":"who has contracts for nuclear waste","session_id":"manual-test","messages":[],"contractor_count":2214,"data_context":""}' \
    | head -5
# Turn 2 (refers back)
sleep 1
curl -s -X POST http://localhost:8765/api/atlas-chat \
    -H "Content-Type: application/json" \
    -d '{"query":"tell me more about the second one","session_id":"manual-test","messages":[],"contractor_count":2214,"data_context":""}' \
    | head -5
kill $SERVER_PID 2>/dev/null
cat logs/atlas_chat.jsonl | tail -2 | python3 -m json.tool
```
Expected: log entries show `intent_classification`, `retrieval_path`, the entity_tracker building up, and turn 2's prompt should include `USER IS CURRENTLY INVESTIGATING:` with at least one contractor name.

- [ ] **Step 8: Commit**

```bash
git add backend/conversation_state.py tests/test_conversation_state.py test_atlas_server.py
git commit -m "feat: rolling conversation summary + entity tracker — Task 7 (final)"
```

---

## Final VALIDATE gate

After all 8 tasks land, run the entire test surface plus the smoke check:

```bash
python3 -m pytest \
    tests/test_atlas_chat_logging.py \
    tests/test_chroma_smoke.py \
    tests/test_atlas_chat_retrieval.py \
    tests/test_intent_router.py \
    tests/test_sql_aggregator.py \
    tests/test_history_budget.py \
    tests/test_conversation_state.py \
    tests/test_hybrid_retriever.py \
    -v 2>&1 | tail -50

python3 -m pytest tests/test_atlas_browser_compat.py --browser chromium --browser firefox --browser webkit -v 2>&1 | tail -20
```

Expected: every test passes. New unit tests count: ~25-30 across the 7 new test files. Browser-compat suite: still 75 (or whatever the current baseline is — report the actual count from pytest output).

**If anything fails:** Do NOT proceed to FINISH. Run the diagnostic phase:
1. Identify which task introduced the regression by `git bisect` if needed
2. Check the chat log file (`logs/atlas_chat.jsonl`) for clues
3. Re-read the integration test spec for the failing task and confirm the behavior matches

## Self-review

- **Spec coverage:** All 8 design moves have a corresponding task with Ground Truth, Provides, Requires, integration test spec, and bite-sized steps. Move 0 = Task 0; Move 1a = Task 1; Move 1b = Task 2; Move 2 = Task 3; Move 3 = Task 4; Move 4 = Task 5; Move 5 = Task 6; Moves 6+7 = Task 7. ✓
- **Placeholder scan:** No TBD/TODO/"similar to". Every code block is complete. ✓
- **Type consistency:** `IntentClassification`, `ContractorRollup`, `ConversationState`, `HybridRetriever.search()`, `HermesClient.chat_structured()` — all signatures match between definition and use sites. ✓
- **Reality check:** Verified directly: `test_atlas_server.py:1100`, `backend/mercury_client.py:106`, `backend/hybrid_retriever.py:40`, `chroma_db/` collection name + count (247,819), `requirements.txt` missing chromadb, frontend telemetry session_id pattern. The one thing I'm assuming without verifying: that Hermes-4-405B's strict-mode JSON Schema actually returns valid results in practice. Task 3 has a fallback to `entity_narrative` on any failure, so even if structured output is flaky, chat keeps working.
