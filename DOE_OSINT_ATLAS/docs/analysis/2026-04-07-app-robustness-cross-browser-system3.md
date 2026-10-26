# System 3 Analysis: App Robustness & Cross-Browser Consistency
Date: 2026-04-07

## Context

**Facts (verified in this session):**
- Main app: `frontend/static/contractor-map.html` — 6,466 LOC vanilla HTML/CSS/JS, loads Leaflet 1.9.4, MarkerCluster 1.5.3, leaflet.heat 0.2.0, d3 7.9.0, and Google Fonts from unpkg / fonts.googleapis.com
- 38 inline event handler attributes; 61 `addEventListener` calls (mixed paradigm)
- Defensive coding patterns are real and applied: 12+ instances each of `100dvh` w/ `100vh` fallback, `-webkit-backdrop-filter` paired with `backdrop-filter`, `pointer-events:none` on click-target children, `isComposing` guard on Enter handler
- Test suite: `tests/test_atlas_browser_compat.py` — **14 test functions** × 3 engines = **42 tests** total
- Playwright 1.58.0 installed; chromium, firefox, webkit binaries present
- Commit `027779c` (risk-label clipping fix) does **not** have a regression test
- **No `.github/` directory** — zero CI, zero merge gates
- Test fixture pins viewport to default (~1280×720); no responsive sweep
- A second frontend exists: SvelteKit at `frontend/src/routes/+page.svelte` with its own ChatPanel/SchematicPanel/Toolbar — has **zero browser tests**

**Unknowns:**
- Whether the existing 42-test suite actually passes right now (commit message claims yes; not yet re-run in this session)
- Whether `test_atlas_server.py` route table / middleware matches the production server entry point
- What viewport sizes real users actually use
- Whether the SvelteKit `/` route is in production scope

**Assumed (NOT verified):**
- The CDN dependencies (unpkg.com) are reliable enough for production
- The `2214` magic number in `test_all_markers_render` matches current data

## Problem Frame

Three framings:
1. *User-facing*: "Some users can't use the app because it breaks on their browser."
2. *Process-facing*: "Cross-browser bugs reach users instead of being caught pre-merge."
3. *Architecture-facing*: "A 6,466-line vanilla-JS file with 38 inline handlers and 14 regression tests is being asked to behave consistently across 3 engines, 4 OSes, unknown viewports."

Numbered assumptions (with confidence):
| # | Assumption | Conf |
|---|---|---|
| A1 | "Robustness" = absence of crashes/visual glitches | M |
| A2 | User cares about end-user bugs more than dev velocity | M |
| A3 | Cross-browser parity is the dominant axis of variation | M |
| A4 | The 14-scenario suite is the right *kind* of test, just incomplete | M |
| A5 | Adding more Playwright tests is the highest-leverage move | **L** |
| A6 | "All browsers" = the four Tier-1 engines in the QA doc | M |
| A7 | The SvelteKit `/` route is out of scope | **L** |
| A8 | The test suite currently passes | M |
| A9 | Tests caught the bugs that recent fixes addressed | **L** |
| A10 | Defensive coding patterns are universally applied | **L** |
| A11 | `test_atlas_server.py` codepath = production codepath | **L** |
| A12 | The 2214-marker assertion is stable | **L** |

## Perspectives

### Skeptic — "You're testing a strawman"
The suite drives `test_atlas_server.py`, which is "lightweight, no ChromaDB." Production uses a different entry. Tests may pass on a server that doesn't match prod, in which case green tests prove nothing. 14 scenarios for 6,466 lines is a coverage joke. Bugs live in interaction sequences, not single function calls.
**Challenges:** A8, A11, A4

### Outsider — Aviation safety engineer — "Defense in depth, with telemetry"
Aviation never assumes pre-flight tests catch everything. They pair tests with **black-box recorders**. When a Firefox user has a problem, your app tells you nothing. Add `window.onerror`, `unhandledrejection`, console-error capture, and a tiny `/api/client-error` endpoint. One day → continuous evidence from real users.
**Challenges:** A1, A5

### Historian — "You've seen this movie before"
Five of the last five commits are cross-browser fixes. Pattern: ship → user reports → fix → backfill test. Tests are necropsies, not prevention. Other large vanilla-JS apps solved this by reducing surface area: split files, lint, render-layer abstraction. A 6,466-line single file is the bug *manufacturing plant*. More tests just measure the output.
**Challenges:** A4, A5, A10

### Futurist — "What gets brittle in 6 months?"
The `2214` magic number breaks when data grows. The pinned `leaflet@1.9.4` from unpkg eventually fails. The Svelte side gets features; nobody writes tests for it. Real risk: the gradual erosion of defenses. Fix: tests that age well, self-host vendor JS, apply QA patterns to Svelte side now.
**Challenges:** A6, A12, A7

### Advocate — DOE analyst on Windows + Firefox ESR + corp proxy — "I just need it to load"
1366×768 screen. Firefox ESR (LTS). Corporate proxy blocks unpkg.com. Page loads → blank screen because Leaflet didn't fetch. No error message. No fallback. No way to report it because the page never finished rendering. **My problem isn't a CSS bug. My problem is the app assumes I have internet to four CDNs.**
**Challenges:** A1, A3, A6

### Conflicts & Agreements
**Universal agreements:**
- Test suite is necessary but insufficient
- More end-to-end tests is NOT the highest-leverage move
- Defensive patterns are real but unevenly enforced

**Conflicts:**
- Skeptic vs Historian — fix test/prod divergence first (measurement bug) vs refactor monolith first (structural bug)
- Futurist vs Advocate — long-term decay vs immediate user pain
- Aviation vs all others — leading prevention vs lagging instrumentation

**Open questions:**
1. Does `test_atlas_server.py` match the production entry point?
2. What CDNs does the page depend on; what happens on failure?
3. Is the SvelteKit `/` route in scope?
4. Leading defenses (more tests, lints) or lagging (telemetry, recovery)?
5. Anything failing right now, or is this a "harden" task?

## Creative Reframes

### Pre-mortem ("It's October 2026; this failed spectacularly")
Senior DOE analyst on Firefox ESR / Windows / corp proxy reports app "broken for the whole team." Can't reproduce. No telemetry. Push blind fix; breaks Chrome. Roll back. Two days lost.
**Root causes that cluster:** No client telemetry. Test/prod drift. Svelte side grew without tests. unpkg outage.

### Inversion: "What if we did NO new end-to-end tests this month?"
- Self-host vendor JS (eliminates 4 SPOFs)
- `window.onerror`/`unhandledrejection` → `/api/client-error`
- CSP header + lint rule banning inline handlers
- CI workflow running existing 42 tests on every PR
- Align test server with prod entry

That's 5 high-leverage moves, none of which add a test, that make existing defenses *count*.

### Analogy from finance: "Build the audit trail before the audit"
Banks log every transaction so fraud is *traceable*. Detection comes later, informed by logs. Apply: log every significant user action and every error for a week, then test the things that actually happened.

## Meta-Cognitive Audit
| Dimension | Score | Evidence |
|-----------|-------|----------|
| Problem definition | 3/5 | "Robustness" still ambiguous; will resolve in DESIGN |
| Assumption validity | 4/5 | 12 numbered, several Low-confidence flagged |
| Perspective diversity | 4/5 | 5 perspectives with genuine conflicts |
| Creative exploration | 4/5 | Pre-mortem + finance analogy + constraint removal |
| Bias awareness | 3/5 | Anchoring caught; availability bias mitigated |

### Active Biases Identified
- **Anchoring** — almost answered "add more tests"; Skeptic/Historian/Aviation forced me off it
- **Availability** — 5 most recent commits are cross-browser fixes, biasing me toward that axis; recommendation explicitly includes non-cross-browser axes (CDN, telemetry)
- **Authority** — trusting QA doc claims; mitigation: spot-check defensive patterns

## Synthesis & Recommendation

### State of robustness — honest assessment

**Good (don't bury):**
- Defensive coding patterns are real and applied
- Working Playwright suite across 3 engines
- QA strategy doc exists and identifies its own gaps
- Recent commits show fast, surgical, well-explained fixes
- Vendor prefixing is consistent
- Test suite pattern is sound

**Structurally weak:**
1. Lagging-only defenses (every test backfilled after a bug)
2. No CI — tests run only when developer remembers
3. Test/prod drift risk (unverified)
4. CDN single-point-of-failure (4 unpkg/google deps, no SRI, no fallback)
5. No client-side error reporting
6. Inline event handlers (CSP-blocking, footgun)
7. No regression test for most recent fix (027779c)
8. Fragile dataset assumption (`2214` magic number)
9. SvelteKit `/` frontend has zero browser tests
10. Tests assert state, not real interactions

### Ranked moves — leading defenses first

| # | Move | Cost | Leverage |
|---|---|---|---|
| 1 | CI workflow running existing 42 tests on every push | 30m | ★★★★★ |
| 2 | Regression test for the 027779c risk-label clipping fix | 15m | ★★★ |
| 3 | Replace hardcoded `2214` with `>= 2200` | 5m | ★★ |
| 4 | Verify `test_atlas_server.py` vs production parity | 30m | ★★★★ |
| 5 | Self-host vendor JS + add SRI hashes | 45m | ★★★★★ |
| 6 | Client-side error telemetry → `/api/client-error` | 45m | ★★★★ |
| 7 | Extract inline `onkeydown` to `addEventListener` | 10m | ★★ |
| 8 | Responsive viewport sweep `(1920,1080)` `(1366,768)` `(1280,720)` | 30m | ★★★ |
| 9 | "No console errors after smoke flow" interaction-sequence test | 30m | ★★★ |
| 10 | CI guard banning inline `on*=` attributes | 15m | ★★ |

**Conscious deferrals:** visual regression (high noise), SvelteKit tests (scope question), 6,466-line refactor (high cost, separate effort), real device cloud (overkill), Lighthouse CI (perf not the stated concern).

## Blind Spots & Uncertainties
1. Test suite not yet run in THIS session — claim of 42/42 pass is unverified
2. Test server vs prod entry not yet diffed
3. SvelteKit `/` scope not confirmed with user
4. Self-hosting vendor JS may break a Leaflet plugin load-order assumption
5. `window.onerror` may catch errors that were always silent — need throttling
6. `2214` may be load-bearing in ways I don't see — grep first
7. Defensive patterns audited only by sampling — not full 6,466-line audit
