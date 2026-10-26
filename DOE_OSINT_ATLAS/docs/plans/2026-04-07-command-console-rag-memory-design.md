# Design: Command Console — Routed Retrieval + Conversation Memory
Date: 2026-04-07
Status: Approved — proceeding to implementation plan

## Problem

The DOE Red Team OSINT Atlas command console has two surface failures the user reports:
1. **Loses the conversation thread after a few turns** — caused by `test_atlas_server.py:1100`, which hard-caps history at the last 6 messages and truncates each to 500 chars (`(msg.get("content") or "")[:500]`).
2. **Useless answers to contract-level questions** like "who has contracts for XYZ" — caused by **two compounding bugs**, neither of which is the bug the user thought they had:

   - **(a)** The production chat handler (`test_atlas_server.py:1087-1157`) does **not call any retriever**. Verified by grep — zero matches for `hybrid_retriever`, `HybridRetriever`, or `retriever.` in the file. The "RAG" the user thinks exists is actually JavaScript substring matching in `frontend/static/contractor-map.html:5965-6038`.
   - **(b)** Even the substring-matched data sent to the LLM contains **zero contract fields**. Lines 5987-5992 of contractor-map.html build per-contractor summary lines with `name | city | risk | dmarc | hosts | vulns` — no `obligation`, no `contract_count`, no `contract_ids`, no contract descriptions. The LLM is told "ONLY reference contractors listed here" but never given the contract data the user is asking about.

A sophisticated 4-lane hybrid retriever (vector + FTS5 + graph + relationship + RRF + optional reranker) **already exists** in `backend/hybrid_retriever.py` with tests in `tests/test_hybrid_retriever.py`. It is wired into a *different* chat handler in `backend/server.py:613-720`. That file was last touched 2026-03-30 (commit `3462dc9 fix: inject real contractor risk data into LLM chat context`). When the unification refactor moved chat into `test_atlas_server.py`, the retriever wiring was dropped and was never restored. **Production has been running without retrieval for 8 days.**

## Goals

1. **Reattach the existing 4-lane hybrid retriever** to production chat — reuse 95% of existing infrastructure rather than introducing new dependencies.
2. **Add intent routing** so aggregate questions ("who has contracts for X") dispatch to a SQL aggregation path instead of vector retrieval, which is the wrong tool for that question category.
3. **Build a real conversation memory architecture** — verbatim recent turns, rolling summary, entity tracker — instead of a brittle turn cap.
4. **Instrument the chat path** so every conversation is captured for diagnosis BEFORE changing behavior. We don't have a real failure repro yet; the Skeptic was right that we should measure before fixing.
5. **No new RAG library.** LightRAG is explicitly out of scope per user decision — the orphaned hybrid retriever covers its main strengths (graph + dual-level retrieval).

## Non-goals

- Replacing `backend/hybrid_retriever.py` with LightRAG or any other library
- Re-indexing the ChromaDB unless verification shows it's stale
- Cross-session conversation persistence (sessions are per-page-load)
- Rebuilding the chat UI
- Changing how contractor data is loaded into the frontend
- Compact-catalog reframe (interesting but unverified — defer to a 10-min prototype during PLAN phase)
- Adding new vendor JS dependencies on the frontend

## The 8 Moves

### Phase A — Instrument (Move 0)

**Move 0 — JSONL conversation logging**
Add server-side logging of every chat turn to `logs/atlas_chat.jsonl` (same JSONL pattern as `client_errors.jsonl`, behind the same `SITE_PASSWORD` cookie gate via `AuthMiddleware`). Each log entry captures:
- `timestamp`, `session_id` (from request payload, generated client-side via `crypto.randomUUID()`)
- `turn_number` within the session
- `query` (user question)
- `intent_classification` (filled by Move 2 once it exists; null until then)
- `retrieval_path` ("vector" | "sql" | "none" | "legacy_substring")
- `retrieval_results_count`, `retrieval_results_preview` (top 3 result strings)
- `prompt_tokens_estimate`, `history_tokens_estimate` (rough char/4 heuristic)
- `full_messages_sent` (the entire message list passed to Hermes — system + history + query)
- `response_text`, `response_time_ms`, `error`
- 16KB cap per entry (truncate response_text first if needed)

**No behavior change in this commit** — purely additive logging. Cost: 30 min.

### Phase B — Reconnect retrieval (Moves 1, 2, 3)

**Move 1 — Reattach the 4-lane HybridRetriever**

Step 1a: **Verify the orphaned retriever still works.** Smoke test by importing and running `HybridRetriever.search("nuclear waste cleanup")` against the existing `chroma_db/`. If it works → proceed. If `chroma_db/` is stale or broken → trigger a re-index via `backend/reingest_chroma.py` first.

Step 1b: **Wire HybridRetriever into `test_atlas_server.py:atlas_chat`** as the "narrative" retrieval path:
```python
# At module init
from backend.hybrid_retriever import HybridRetriever
from backend.graph_engine import GraphEngine

_retriever = None
def get_retriever():
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever(
            db_path="doe_contracts.db",
            graph_engine=GraphEngine(),  # if available
            chroma_path="chroma_db",
            ollama=ollama,
        )
    return _retriever
```

Then in `atlas_chat`, after the intent router classifies a query as `entity_narrative`, call `get_retriever().search(query)` and inject the top 15 results as a `RELEVANT CONTRACT DATA:` block in the prompt — same pattern as `backend/server.py:621-624`.

**Fallback:** If `HybridRetriever` initialization fails (chroma missing, graph missing), log the failure and fall through to the legacy substring path so chat doesn't break. We never want a retrieval failure to take down the chat.

Cost: 1-2h.

**Move 2 — Intent router**

Add a function `classify_intent(query: str, recent_history: list[dict]) -> IntentClassification` that calls Hermes-4-405B with a structured-output prompt and returns:
```python
class IntentClassification(BaseModel):
    intent: Literal["aggregate", "entity_narrative", "action", "smalltalk"]
    confidence: float  # 0.0-1.0
    search_terms: list[str] = []   # for SQL LIKE or vector retrieval
    filters: dict = {}              # optional: state, fiscal_year, agency, min_value
    target_contractor: str | None   # for entity_narrative on a specific contractor
```

**Why LLM-based, not rules-based:** A 50-line keyword regex would catch "who has" / "how many" / "list contractors" easily — but would fail on "give me everyone working on hypersonics in California" (an aggregate-with-filters question with no trigger keywords). One Hermes call (~150-300ms) is the right tradeoff for round 1. We can add a rules-based fast path later if latency matters.

The router is called BEFORE retrieval. Its output drives which retrieval path runs (or whether to skip retrieval entirely for `smalltalk`).

**Cache:** Cache the last `(query, intent)` pair in memory to short-circuit duplicate queries.

Cost: 1h.

**Move 3 — SQL aggregator**

Add `aggregate_contracts(search_terms: list[str], filters: dict, limit: int = 20) -> list[ContractorRollup]` in a new module `backend/sql_aggregator.py`:

```python
@dataclass
class ContractorRollup:
    recipient_name: str
    contract_count: int
    total_obligation: float
    fiscal_years: list[int]
    top_psc: list[str]
    top_naics: list[str]
    sample_descriptions: list[str]  # 3 representative

def aggregate_contracts(search_terms, filters, limit=20):
    # WHERE: (transaction_description LIKE ? OR psc LIKE ? OR naics LIKE ?) AND ...
    # SELECT recipient_name, COUNT(*), SUM(federal_action_obligation), ...
    # GROUP BY recipient_name
    # ORDER BY SUM(federal_action_obligation) DESC LIMIT ?
    ...
```

When the intent router returns `intent=aggregate`, dispatch to `aggregate_contracts(...)` and inject the rollups as a `CONTRACTOR ROLLUPS (matching your query):` block in the prompt. The LLM then formats and presents them.

**Why SQL not vector retrieval:** Vector retrieval returns top-k chunks. The user's question "who has contracts for X" is a `GROUP BY recipient` over potentially hundreds of matching rows. No amount of vector retrieval can produce a `COUNT(*)` or `SUM(obligation)`. SQL is the only correct tool here.

**Synonym handling:** Round 1 uses simple LIKE. If the user reports problems like "nuclear waste" missing "radioactive cleanup," we can add a synonym layer — but punt that until we have evidence (Move 0 logs).

Cost: 2h.

### Phase C — Real memory architecture (Moves 4, 5, 6, 7)

**Move 4 — Token-budgeted history**

Replace `test_atlas_server.py:1100`:
```python
history = list(req.messages[-6:])
```
with:
```python
history = budget_history(req.messages, target_tokens=8000)
```

Where `budget_history` walks backwards from the newest message and includes turns until the token budget is hit. Token estimation: `len(content) // 4 + 10`. Drop the per-message 500-char truncation entirely.

This is a leaf-level fix and might be enough on its own to fix Failure Mode #1. The next 3 moves add architecture for cases where it isn't.

Cost: 30m.

**Move 5 — Server-side ConversationState**

New module `backend/conversation_state.py`:
```python
@dataclass
class ConversationState:
    session_id: str
    verbatim_turns: list[dict]            # [{role, content}, ...]
    rolling_summary: str = ""             # filled by Move 6
    entity_tracker: list[str] = field(default_factory=list)  # filled by Move 7
    created_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)
    turn_count: int = 0

class ConversationStore:
    def __init__(self, max_sessions: int = 200, ttl_seconds: int = 3600):
        self._sessions: dict[str, ConversationState] = {}
        self._max = max_sessions
        self._ttl = ttl_seconds

    def get_or_create(self, session_id: str) -> ConversationState: ...
    def evict_expired(self) -> None: ...  # called on every get
    def append_turn(self, session_id: str, role: str, content: str) -> None: ...
```

Frontend payload gains a `session_id` field — **reuse the existing telemetry session id** from `frontend/static/contractor-map.html` (the `setupErrorTelemetry` IIFE already generates one via `crypto.randomUUID()`). One source of truth for sessions across telemetry + chat.

Backend uses `ConversationStore` instead of `req.messages` as the authoritative history source. The frontend can still send `req.messages` as a fallback for the first request after a server restart (when state would be lost).

**Memory bound:** 200 sessions × ~50KB per session = ~10MB max RAM. TTL evicts idle sessions after 1 hour. Eviction runs lazily on every `get_or_create` call.

Cost: 1h.

**Move 6 — Rolling conversation summary**

When `len(verbatim_turns)` would push history above the 8K token budget, run a single Hermes call to summarize the oldest N turns into a 200-token "PRIOR DISCUSSION SUMMARY" string, store it on `ConversationState.rolling_summary`, and trim those turns from `verbatim_turns`. The summary is then injected into the system prompt as:

```
PRIOR DISCUSSION SUMMARY:
{rolling_summary}

RECENT CONVERSATION:
{last K verbatim turns}
```

**When to regenerate:** Only when verbatim history would *otherwise* be truncated. Don't regenerate every turn — too expensive. The summary itself can be re-summarized (summary-of-summary) when it grows large, but for round 1 a single summary is enough.

Cost: 1h.

**Move 7 — Entity tracker**

On every user message AND every assistant message, scan for contractor names from `contractors.json` (load once into a sorted list of `(name, idx)` tuples). Use a fast string match (Aho-Corasick is overkill — a simple loop with `name.lower() in text.lower()` over 2,214 names is ~50ms per message and good enough). Append matches to `ConversationState.entity_tracker`, dedupe, keep the most-recently-mentioned 10.

Inject into the system prompt as:
```
USER IS CURRENTLY INVESTIGATING: {entity_tracker[:10]}
```

This lets the LLM resolve references like "and what about the second one?" — the entity tracker tells it which "second one" was on the table.

Cost: 1h.

## Frontend changes (minimal)

1. Send `session_id` (already generated by the telemetry IIFE — just lift it out of that scope into a module-level variable and add to chat payload)
2. **No removal of the existing `messages` field** — keep it as a fallback for the first request after a server restart, but the server prefers `ConversationStore` state when present
3. No UI changes

## Testing strategy

**Unit tests (per move):**
- Move 0: log entry structure and JSONL append
- Move 1: HybridRetriever initialization succeeds against current `chroma_db/`; retriever returns results for known queries
- Move 2: intent router classifies a fixed test set of 10 queries correctly (3 aggregate, 3 narrative, 2 action, 2 smalltalk)
- Move 3: `aggregate_contracts(["nuclear waste"], {})` returns rollups with non-zero `contract_count` and `total_obligation`
- Move 4: `budget_history` returns correct subset of messages for target budgets
- Move 5: `ConversationStore` enforces TTL and max-session bounds; round-trips state correctly
- Move 6: rolling summary regenerates only when budget exceeded; summary is non-empty
- Move 7: entity tracker extracts contractor names correctly; ordering by recency

**Integration tests:**
- End-to-end chat turn: query → intent classification → dispatch → retrieval/aggregation → prompt build → mocked LLM call → response → state update. Mock Hermes; assert the prompt structure matches expectations for each intent path.
- Multi-turn: 15-turn conversation, assert that earliest turns are summarized into `rolling_summary` and that turn 15's prompt still references entities from turn 1
- Failure mode: kill the retriever mid-request, assert the legacy substring path takes over and chat still completes

**Manual validation:**
- After Move 0: confirm logs appear in `logs/atlas_chat.jsonl` with full prompt + response
- After Move 1: ask "tell me about Lawrence Livermore's cybersecurity posture" → assert response references contracts from the retriever
- After Move 3: ask "who has contracts for radiation hardening?" → assert response is a list of recipients with $$ totals, not snippets
- After Move 4-7: 15-turn conversation testing memory recall on early turns

## Implementation order and commit grouping

8 commits, one per move (Move 1 split into 1a verify + 1b wire if verification reveals stale chroma):

1. **Commit 1 — Move 0:** JSONL conversation logging (no behavior change)
2. **Commit 2 — Move 1a:** Smoke test orphaned HybridRetriever; verify chroma_db freshness; trigger reingest if needed (commit may be empty if no reingest needed)
3. **Commit 3 — Move 1b:** Wire HybridRetriever into test_atlas_server.py atlas_chat as the entity_narrative path; add fallback to legacy substring on failure
4. **Commit 4 — Move 2:** Intent router (LLM-based with structured output)
5. **Commit 5 — Move 3:** SQL aggregator + dispatch from intent=aggregate
6. **Commit 6 — Move 4:** Token-budgeted history (replace 6/500 cap)
7. **Commit 7 — Move 5:** Server-side ConversationState + frontend session_id wiring
8. **Commit 8 — Moves 6+7 bundled:** Rolling summary + entity tracker (live in same module, share access patterns)

Each commit independently revertable. CI must run after every commit (the existing browser-compat workflow + a new chat unit-test workflow we add as part of Move 0).

## Success criteria

1. After Move 0: `logs/atlas_chat.jsonl` exists and accumulates one entry per chat turn during normal use
2. After Move 1: real query "tell me about Honeywell's cybersecurity work" returns response containing actual contract descriptions (not just contractor metadata)
3. After Move 2: 8/10 of the test query set is classified correctly into the right intent bucket
4. After Move 3: query "who has contracts for nuclear waste" returns a ranked list of recipients with `contract_count` and `total_obligation`, not chunks
5. After Move 4: a 15-turn conversation retains references to turn 1 entities at turn 15 (verified by injecting "remember I asked about X earlier" at turn 15)
6. After Move 5: `ConversationStore` survives 200 sessions without crashing; idle sessions evict after 1 hour
7. After Move 6: a 30-turn conversation has turns 1-20 summarized into `rolling_summary` while still being referenced correctly
8. After Move 7: a query "and what about the second one?" after listing 3 contractors resolves correctly to the second contractor without ambiguity

## Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Orphaned HybridRetriever has rotted in 8 days (broken imports, stale chroma) | M | M | Move 1a verifies before Move 1b. If broken, re-index via `backend/reingest_chroma.py` before wiring |
| `chroma_db/` directory is missing or empty in the deploy environment | M | H | Add a startup check that logs a warning and falls back to legacy substring path; document the reingest command |
| Intent router misclassifies and sends aggregate questions to vector retrieval | H (round 1) | M | Test set of 10 queries; iterate the prompt; add a rules-based fast path in round 2 if needed |
| LLM call for intent routing adds 200ms+ latency to every chat turn | H | M | Cache `(query, intent)` pairs; consider a smaller/faster model for the router specifically (Hermes is large) |
| SQL `LIKE` queries miss synonym variants ("nuclear" vs "radioactive") | M | M | Punt to round 2; add synonym layer or query expansion only if logs show real misses |
| Server-side ConversationState introduces memory leak | M | M | TTL eviction + max-session cap; integration test for eviction behavior |
| Frontend session id mismatch between telemetry and chat | L | L | Lift the existing telemetry session id to module scope; share one source of truth |
| The fix is "too" successful and the user generates 100x more chat traffic, exhausting Hermes API quota | L | L | Existing rate limits on `/api/atlas-chat` should already cover this; verify |
| A regression in the chat path takes down the production deploy | M | H | Each commit independently revertable; legacy substring path stays as fallback through Move 3; Railway deploy is 1-commit revert away |

## Rollback

Each commit is independently revertable. The riskiest commits are 3 (wiring retriever) and 7 (server-side state). If either breaks production:
- `git revert <commit>` restores previous behavior
- The legacy substring path (currently in production) stays in the code as a fallback through all 8 commits — it only gets removed in a hypothetical Commit 9 (out of scope for this design)

## Open questions (none blocking)

None. All decisions are resolved:
- LightRAG: out of scope (user accepted reframing)
- Server-side state: yes (user picked option)
- Sequencing: parallel measure + reconnect (user picked option)
- Intent router style: LLM-based for round 1 (chosen in design — can revisit)
- Synonym handling: deferred (chosen in design)
- Compact-catalog reframe: deferred (interesting but unverified)
