# System 3 Analysis: AI Research Layer
Date: 2026-04-02

## Context

**Task:** Build a 13th OSINT pipeline layer that uses Hermes-4-405B + Brave Search to research each of 2,214 DOE contractors — find correct domains, determine company status (active/acquired/dissolved), trace acquisition chains, produce structured intelligence briefs with sources.

**Known Facts:**
- 2,214 contractors in contractors.json, many with wrong domains from DNS heuristic probing
- Existing Brave Search domain validation layer catches some errors but fails for acquired/renamed companies (OSI Inc → osii.com is defunct, real parent is Emerson/AspenTech)
- HermesClient provides `chat()`, `chat_stream()`, `chat_structured()` (json_schema response format)
- BraveSearchClient provides `search()` (returns title/url/description dicts) and `search_for_context()` (markdown formatted)
- Pipeline layers follow pattern: `needs_layer()` check → process → store in `osint[layer_name]` → save periodically
- Domain cascade pattern exists: domain change → invalidate downstream layers (verify, dns, ct, web)
- `summarize-role` endpoint already does Brave + Hermes synthesis per contractor (on-demand SSE)
- The frontend detail panel renders dynamic sections in panelBody

**Unknown:**
- Brave Search API monthly call limits (code uses 0.5s delay)
- Nous Research API rate limits/costs for 2,214+ LLM calls
- What percentage of contractors have incorrect domains
- Whether `chat_structured()` is reliable enough for batch use
- Whether Gemini CLI is available on this machine

**Assumed → Verified in Phase 1**

## Problem Frame

### Stated 3 Ways

1. **Domain accuracy:** DNS heuristic probing produces wrong domains for companies whose domain doesn't match their name, companies that have been acquired/merged, and small companies with generic names. An AI reasoning layer can search the web and deduce the correct current domain.

2. **Intelligence gap:** We have mechanical OSINT data (ports, CVEs, DNS) but no contextual intelligence about what each contractor does, whether they still exist, or who owns them. The AI Research Layer fills this with structured intelligence briefs.

3. **Pipeline maturity:** 12 layers of scanners, zero layers of reasoning. The 13th layer thinks like an analyst — synthesizing web evidence into actionable intelligence.

### Assumptions (Numbered)

1. **Hermes + Brave is sufficient** — No need for Gemini CLI; the existing stack handles web search + LLM synthesis.
2. **Batch-first architecture** — Pipeline processes all contractors offline; on-demand is secondary.
3. **chat() with JSON extraction > chat_structured()** — Manual JSON extraction from `chat()` is more reliable than `chat_structured()` based on codebase patterns (kill_chain, saturate all use manual extraction with fallbacks).
4. **3-5 Brave searches per contractor is enough** — Company+DOE, acquisition/merger, current website, domain verification.
5. **The LLM can classify company status** — Active, acquired, merged, dissolved — distinguishable from web evidence.
6. **Smart targeting reduces batch size** — Contractors with brave_search-validated, high-confidence domains don't need AI research. Estimate: 800-1,200 need it.
7. **Rate limits are manageable** — 0.5s between Brave calls, 2-3s between Hermes calls, with checkpointing.
8. **Domain cascade pattern is reusable** — Same invalidation logic from domain_search layer.
9. **LLM confidence scores provide useful signal** — Self-reported confidence (0-100) helps triage.
10. **Frontend section follows existing panel pattern** — New section + optional on-demand button.

### What If I'm Framing This Wrong?

Maybe the real fix is a better data source — SAM.gov has authoritative contractor URLs. Or commercial providers (ZoomInfo, Crunchbase) maintain acquisition chains. The AI Research Layer might be overengineering what a single API call to a commercial database would solve. **Counter:** SAM.gov URLs are often wrong/outdated too. Commercial APIs cost $$$/month. The AI approach adapts to any company, traces current state, and produces intelligence — not just a URL.

## Perspectives

### Skeptic
"You're building a custom web-search-to-LLM pipeline for something commercial data providers solve better. ZoomInfo tracks M&A, domain changes, and company status. The LLM adds hallucination risk — it might confidently declare a company 'acquired by Emerson' from a tangentially related search result. And structured JSON from an LLM? That's a 3-hour batch run waiting to fail at contractor #1,847 because the JSON was malformed."

- Challenges assumption #1 (Hermes+Brave sufficiency) and #5 (LLM classification accuracy)
- Sees: hallucination as the critical risk, commercial data as simpler

### Operator
"The summarize-role endpoint already does 80% of this. Brave search + Hermes synthesis, streaming progress. The pipeline version is just the batch equivalent. Don't overthink — extend what works. But add retry logic, progress checkpointing every 25 contractors, and resume from where you left off. The 3-hour runtime is the real risk. Also: validate every LLM domain claim — DNS-probe it before trusting it."

- Challenges assumption #2 (batch-first) — emphasizes resumability
- Sees: operational reliability as the main engineering challenge

### Historian
"Every pipeline layer follows the same pattern. `run_layer_domain_search` is the closest precedent — async, uses Brave, cascades domain upgrades. The `summarize-role` endpoint is the closest on-demand precedent. Follow both patterns. Don't invent new abstractions. The codebase has 12 layers that all look alike — make it 13."

- Supports assumption #8 (cascade reuse) and #10 (frontend pattern)
- Sees: pattern consistency as non-negotiable for maintainability

### Futurist
"In 6 months, analysts will want to click 'Research' and get fresh intelligence, not just cached batch results. Build both modes from the start: the pipeline populates the base data, the endpoint refreshes individual contractors on demand. The research function should be usable from both contexts."

- Challenges assumption #2 (batch-only)
- Sees: dual-mode (batch + on-demand) as essential from day one

### Advocate (Analyst User)
"When I click a contractor, I want to know: Is this company still around? Who owns them now? What's their real website? What do they actually do for DOE? Give me sources I can click. The intelligence brief should be the FIRST thing I see — it's the context that makes the technical OSINT meaningful. And if the domain was wrong, I want to see that it was corrected and why."

- Supports the feature's value proposition
- Sees: the brief + sources as the primary deliverable, domain correction as secondary

### Conflicts & Agreements

**Agreements:**
- Feature is needed, extends existing patterns
- Domain validation must include DNS probe verification
- Resumability/checkpointing is critical for batch runs
- Sources must be auditable (store raw search results)

**Conflicts:**
- Skeptic wants commercial data; others want to extend existing Brave+Hermes
- Futurist wants dual-mode from day one; Historian wants minimal pattern deviation
- Skeptic worries about hallucination; Advocate wants rich intelligence

**Resolution:** Build on existing patterns (Historian wins on architecture), add both batch + on-demand (Futurist wins on scope), validate LLM claims with DNS probing (Skeptic's concern addressed), store raw search results for auditability (Skeptic + Advocate both satisfied).

## Creative Reframes

### Inversion: "What if we only research contractors that need it?"
Smart targeting: Skip contractors with brave_search-validated domains and high confidence (>70%). Only research: no domain, dns_probe source, low confidence, or never domain-searched. This could reduce batch from 2,214 to ~800-1,200 — saving 40-50% of API calls.

### Pre-mortem: "It failed. Why?"
Three months later, the AI Research Layer is abandoned because:
- (a) Brave Search returned irrelevant results for 30% of small/obscure companies → **Fix:** Detect low-signal results (no name match in titles), mark as "inconclusive" instead of guessing
- (b) The LLM hallucinated acquisition chains for 5% of companies → **Fix:** Require the LLM to cite specific search result URLs for every claim; validate domain claims with DNS probe
- (c) The batch took 6 hours and crashed at 60% → **Fix:** Save every 25 contractors, track progress with `queried` flag, resume from last checkpoint
- (d) JSON parsing failed for 10% of responses → **Fix:** Use `chat()` not `chat_structured()`, extract JSON between first `{` and last `}`, multiple fallback strategies

### Analogy: "How would an intelligence analyst research a company?"
1. Search for the company name + context (DOE, energy, federal contractor)
2. Check if the company still exists — look for "acquired by", "merged with", "dissolved"
3. Find the current website — follow acquisition chains to the parent
4. Verify the website is real — check it resolves, check the content mentions the company
5. Write a brief — who they are, what they do, current status, sources

The AI Research Layer follows this exact workflow with Brave Search (steps 1-3), DNS probe (step 4), and Hermes synthesis (step 5).

## Meta-Cognitive Audit

| Dimension | Score | Evidence |
|-----------|-------|---------|
| Problem definition clarity | 5/5 | Three clear framings, all converge on same need |
| Assumption validity | 4/5 | Weakest: #5 (LLM classification) and #7 (rate limits). Mitigated by validation and checkpointing |
| Perspective diversity | 4/5 | 5 genuine perspectives with real conflicts. Skeptic raised commercial alternatives. |
| Creative exploration | 4/5 | Smart targeting reduces scope 40-50%. Pre-mortem identified 4 failure modes with fixes. |
| Bias awareness | 4/5 | Possible sunk-cost bias toward Hermes+Brave (already integrated). But extending existing stack IS the pragmatic choice. |

### Active Biases Identified
- **Sunk cost:** We have Hermes+Brave integrated → tendency to use them. Mitigated: they genuinely ARE the right tools here.
- **Anchoring:** The summarize-role endpoint anchors our thinking. Mitigated: we're extending it, not copying it — adding structured output, domain correction, and batch mode.
- **Optimism:** Assuming 3-5 searches per contractor is enough. Mitigated: pre-mortem identified "inconclusive" results as a failure mode.

All scores ≥ 3. Proceeding to Synthesis.

## Synthesis & Recommendation

### Architecture: Dual-Mode AI Research Layer

**Core module:** `osint/ai_research.py`
- `async research_contractor(contractor, hermes, brave) → dict` — the shared research function
- Performs 3-5 Brave searches per contractor (name+DOE, acquisition, website, domain verification)
- Feeds search results + contractor record to Hermes for structured synthesis
- Extracts JSON with fallback parsing (same pattern as kill_chain.py)
- Validates domain claims with DNS probe before committing
- Returns structured dict:
  ```json
  {
    "queried": true,
    "query_time": "ISO timestamp",
    "company_status": "active|acquired|merged|dissolved|unknown",
    "current_domain": "example.com",
    "domain_confidence": 85,
    "domain_source": "ai_research",
    "parent_company": "Emerson Electric",
    "acquisition_year": 2020,
    "brief": "2-3 paragraph intelligence brief",
    "sources": [{"title": "...", "url": "..."}],
    "search_queries_used": 4,
    "error": null
  }
  ```

**Pipeline layer:** `run_layer_ai_research(contractors)` in `osint/pipeline.py`
- Smart targeting: only contractors needing research (no domain, dns_probe, low confidence)
- Async batch with 1-2s delays between contractors
- Checkpoints every 25 contractors
- Domain cascade on correction (same pattern as domain_search)
- CLI: `--layers ai_research`

**On-demand endpoint:** `/api/ai-research` in `test_atlas_server.py`
- SSE streaming: search → synthesis → complete phases
- Takes contractor_index, returns research result
- Saves result to contractors.json

**Frontend:** New "AI Research" section in detail panel
- Shows brief, company status badge, domain correction note, clickable sources
- "Research" button triggers on-demand generation for contractors without cached results

### Key Design Decisions

1. **Use `chat()` + manual JSON extraction** over `chat_structured()` — more reliable based on codebase precedent
2. **Smart targeting** — don't research contractors that already have good data
3. **Validate before trust** — DNS-probe every LLM-suggested domain before committing
4. **Store raw search results** — for auditability and re-analysis
5. **Dual-mode from day one** — batch pipeline + on-demand endpoint share the same core function

## Blind Spots & Uncertainties

1. **Brave Search API limits** — Unknown monthly cap. 800-1,200 contractors × 4 searches = 3,200-4,800 calls. May hit limits.
2. **LLM acquisition chain accuracy** — Complex M&A (OSI → Emerson → AspenTech → Emerson again) may confuse the LLM.
3. **Small company coverage** — Companies with <50 employees and no web presence may yield zero useful search results.
4. **Cost** — Nous Research API pricing for 800-1,200 LLM calls is unknown.
5. **Stale data** — Research results age. No mechanism for scheduled refresh (future work).
