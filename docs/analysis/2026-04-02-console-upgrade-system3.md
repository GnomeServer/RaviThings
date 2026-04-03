# System 3 Analysis: Command Console Upgrade
Date: 2026-04-02

## Context

**Task:** Upgrade the OSINT Atlas command console with three levels: (1) Action Commands — LLM triggers workflows like kill chains, AI research, exports; (2) Multi-Step Reasoning — agentic loop for complex analytical queries; (3) Spatial + Session Memory — radius queries, contextual follow-ups.

**Known:**
- Chat endpoint: `/api/atlas-chat` in test_atlas_server.py (line 667)
- MAP_CMD protocol: 5 actions (fly_to, filter, reset, open_panel, highlight)
- MAP_CMD extraction happens during token streaming (lines 704-727)
- Frontend dispatches MAP_CMDs via `executeMapCommand()` (line 5791)
- Conversation history: client-side array, last 10 sent to server, server uses last 6
- Data context: up to 60 contractor summaries sent per query
- Existing action endpoints: /api/ai-research, /api/kill-chain, /api/full-assessment, /api/summarize-role
- HermesClient has chat() and chat_stream() — non-streaming and streaming
- Frontend has all contractor data loaded in memory (DATA.contractors)

**Unknown:**
- Whether Hermes can reliably produce multi-step action plans
- Token budget constraints when combining system prompt + data context + history + multi-step reasoning
- Whether the LLM will correctly choose when to use action commands vs just answer

## Problem Frame

### Stated 3 Ways

1. **Capability gap:** The console can display and filter but can't act. "Run a kill chain on ORNL" requires clicking buttons, not typing commands. The console should be the primary interface for ALL platform capabilities.

2. **Intelligence workflow gap:** Real analysis is multi-step — filter, cross-reference, analyze, act. The console does single-turn Q&A. It should support the iterative, building-up nature of real intelligence work.

3. **Spatial awareness gap:** The data has lat/lon but the console can't think spatially. "Show me contractors within 50 miles of Oak Ridge" is a basic geo-intelligence query that should work.

### Assumptions

1. **The MAP_CMD protocol is the right extension point** — adding new action types to an existing, working protocol is safer than inventing a new mechanism.
2. **Action commands should execute client-side** — the frontend already has the functions (generateAIResearch, generateKillChain). New MAP_CMDs just call them.
3. **Multi-step reasoning needs a backend loop** — the LLM generates a plan, the backend executes steps, feeds results back for the next step.
4. **Session memory lives client-side** — the frontend already maintains `atlasChatMessages` and active filter state. We enhance this, not replace it.
5. **Spatial queries are pure client-side math** — haversine distance computed in JS from lat/lon already in DATA.contractors.
6. **The system prompt is the control mechanism** — we add new command docs and behavioral rules to the system prompt to enable new capabilities.
7. **Token budget is tight** — system prompt + 60 contractor summaries + 6 history messages + user query is already substantial. Multi-step reasoning can't add unlimited context.
8. **Hermes can produce structured commands reliably** — it already produces MAP_CMDs correctly; more command types should work.

## Perspectives

### Skeptic
"Multi-step agentic reasoning with Hermes-4-405B? The model will hallucinate steps, get confused about state, and produce worse results than single-turn. The existing MAP_CMD protocol works because the commands are simple — fly_to, filter, reset. Adding action commands that trigger 30-second workflows mid-conversation will create confusing UX."

- Challenges assumption #3 (multi-step needs backend loop) — maybe keep it simple
- Sees: complexity risk, UX confusion from long-running actions in chat

### Operator
"The architecture is already in place. The frontend has functions for every action. The MAP_CMD dispatcher is a switch statement. Adding cases is trivial. The hard part is the system prompt — teaching the LLM when to use which command. And testing — you need to verify every command works through the full pipeline."

- Supports assumption #1 (MAP_CMD is right extension point)
- Sees: prompt engineering and integration testing as the real work

### Advocate (Analyst User)
"I want to type 'research the top 5 highest-risk contractors in Tennessee' and have the system do it. I don't want to click Research 5 times. I want to say 'compare ORNL and LANL security posture' and see a comparison. The console should be how I drive the entire platform."

- Supports all three levels
- Sees: the console as the analyst's primary workflow tool

### Futurist
"Session memory is the foundation for collaborative intelligence. Today it's one analyst's session. Tomorrow it's a shared workspace where multiple analysts build on each other's queries. The filter state, the research results, the kill chains — they should persist and be shareable."

- Challenges assumption #4 (session memory client-side only)
- Sees: persistence and collaboration as the long game

### Historian
"The MAP_CMD protocol already works. Every upgrade should be additive — new action types, not new protocols. The existing streaming architecture handles MAP_CMDs mid-token-stream. Keep that. Don't restructure."

- Supports assumption #1 strongly
- Sees: additive extension as the safest path

### Agreements
- All agree MAP_CMD extension is the right approach
- All agree action commands are highest priority
- All agree session memory enables everything else

### Conflicts
- Skeptic vs Advocate on multi-step complexity
- Operator vs Futurist on client-side vs persistent state

### Resolution
Build all three levels but in order of increasing complexity. Level 1 (action commands) is pure additive extension — new MAP_CMD types, new switch cases, updated system prompt. Level 2 (multi-step) adds the agentic loop but can fail gracefully to single-turn. Level 3 (spatial + memory) is client-side math + enhanced state tracking.

## Creative Reframes

### Inversion: "What if the LLM doesn't control actions at all?"
Instead of MAP_CMD-triggered actions, what if the frontend detects intent? "Research ORNL" → frontend recognizes the pattern and triggers the action directly, no MAP_CMD needed. **Counter:** This limits the LLM's ability to compose actions in creative ways. MAP_CMD is better because the LLM can chain commands.

### Pre-mortem: "The console upgrade failed. Why?"
(a) The system prompt got too long and the LLM started ignoring instructions. **Fix:** Keep new command docs concise. (b) Multi-step queries took 2+ minutes and the user gave up. **Fix:** Show step-by-step progress in chat. (c) The LLM used action commands when the user just wanted information. **Fix:** Clear rules in system prompt about when to use action vs info. (d) Session memory ate the token budget. **Fix:** Compress old context, only send relevant filter state.

## Meta-Cognitive Audit

| Dimension | Score | Evidence |
|-----------|-------|---------|
| Problem definition | 5/5 | Three clear levels, each building on the last |
| Assumption validity | 4/5 | Weakest: #3 (multi-step backend loop), #7 (token budget) |
| Perspective diversity | 4/5 | Skeptic raised real concerns about multi-step complexity |
| Creative exploration | 4/5 | Pre-mortem identified 4 failure modes with mitigations |
| Bias awareness | 4/5 | Possible feature-creep bias — mitigated by building in order |

## Synthesis & Recommendation

### Architecture: Additive MAP_CMD Extension

**Level 1: Action Commands (4 new MAP_CMD types)**

New actions added to `executeMapCommand()`:

| Action | Parameters | What It Does |
|--------|-----------|--------------|
| `research` | `contractor_index` | Calls `generateAIResearch()`, streams progress into chat |
| `kill_chain` | `contractor_index` | Calls `generateKillChain()`, renders result inline |
| `assess` | `contractor_index` | Calls `generateFullAssessment()` |
| `export_csv` | `filter` (optional) | Generates CSV download from currently visible contractors |
| `compare` | `contractor_indices: [int]` | Side-by-side comparison table in chat |
| `radius` | `lat, lon, miles` | Filter to contractors within radius, draw circle on map |

**System prompt additions:** Document new commands with usage rules. Key rule: "Use action commands when the user asks you to DO something (research, analyze, compare, export). Use filter/fly_to when the user asks to SEE something."

**Level 2: Multi-Step Reasoning (agentic loop)**

Backend change: after the LLM's first response, check if it emitted a `THINK_STEP` marker. If so, execute the MAP_CMDs, collect results (filter counts, contractor data), and feed back to the LLM for the next step. Max 5 steps.

New system prompt section:
```
MULTI-STEP ANALYSIS: For complex queries requiring multiple steps:
1. Think through your plan
2. Execute one MAP_CMD at a time
3. Observe the result
4. Decide next step or conclude
Emit ANALYSIS_STEP:{"step":1,"description":"Filtering to critical-risk contractors"} before each step.
```

**Level 3: Spatial + Session Memory**

- `radius` MAP_CMD: haversine distance computed in frontend JS
- Leaflet circle overlay drawn on map
- Session state: track active filters, last referenced contractors, and analysis context
- Enhanced history: send filter state + referenced contractor indices with each query
- Follow-up queries: "now filter those to just the ones with exposed RDP" works because the frontend knows what "those" means

### Implementation Order
1. **Action commands** — extend MAP_CMD protocol, update system prompt, frontend dispatcher
2. **Spatial queries** — radius command, circle overlay, haversine math
3. **Session memory** — filter state tracking, context compression
4. **Multi-step reasoning** — agentic loop in backend, step-by-step UI
5. **Compare command** — comparison table renderer

## Blind Spots
- Token budget under multi-step: each step adds context, may overflow
- LLM may over-use action commands when info-only response is appropriate
- Export CSV from client-side may hit browser memory limits for large datasets
- Circle overlay needs cleanup when filters change
