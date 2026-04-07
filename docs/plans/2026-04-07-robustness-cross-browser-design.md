# Design: App Robustness & Cross-Browser Consistency Hardening
Date: 2026-04-07
Status: Draft — awaiting user review

## Problem

Robustness and cross-browser consistency improvements for the DOE Red Team OSINT Atlas. The last 5 commits on master are all cross-browser bug fixes, and the QA doc explicitly acknowledges gaps. The existing defenses are *real but incomplete*: a 42-test Playwright suite exists, defensive coding patterns are applied, a QA strategy doc exists — but CI is manual, telemetry is nonexistent, and several structural weaknesses leak bugs to users.

This design covers the high-leverage cluster identified in `docs/analysis/2026-04-07-app-robustness-cross-browser-system3.md`.

## Goals

1. **Eliminate the "forgot to run tests" class of regression** — every push runs the existing 42-test suite automatically.
2. **Eliminate CDN single-points-of-failure** — the app must load and be usable even when unpkg.com / Google Fonts is unreachable.
3. **Replace the "user reports, developer guesses" feedback loop** with client-side error telemetry — real errors get captured, logged, and reviewable.
4. **Close regressions from the backfill-gap** — every fix commit in the last cycle gets a regression test, including the most recent one that doesn't have one yet.
5. **Harden the test suite itself** — remove magic numbers, add responsive viewport coverage, add an interaction-sequence smoke test, and add a CI lint guard to prevent the inline-handler class from returning.

## Non-goals

- Rewriting the 6,466-line monolith into components (separate, much larger effort)
- Browser tests for the SvelteKit `/` route — **confirmed not deployed** (test_atlas_server.py redirects `/` → `/atlas`; `frontend/build/` exists but isn't served)
- Visual regression / pixel diffs (high noise, defer until CI + telemetry mature)
- Real device cloud (BrowserStack) — overkill before exhausting local Playwright
- Lighthouse CI (perf not the stated concern)
- Deleting vestigial SvelteKit code (separate question)

## Key finding flagged from System 3 analysis

`test_atlas_server.py` IS the production entry point.
- `Procfile`: `web: python test_atlas_server.py`
- `railway.toml`: `startCommand = "python test_atlas_server.py"`
- `Dockerfile`: `CMD ["python", "test_atlas_server.py"]`

The name is a historical artifact from when it was intended as a lightweight test harness. Production has been using it as the live server since the Railway deployment commits. **There is no test/prod drift.** This is good news — it means the existing 42-test suite is testing the actual production codepath.

## The 10 Moves

### Phase A — Baseline verification (Task 0)

Before changing anything: run the existing 42-test suite and record the baseline. If any test fails, the design pauses and we diagnose first. No "fix forward" until we know the starting state.

### Phase B — Leading defenses (high leverage, low cost)

**Move 1 — CI workflow**
Add `.github/workflows/browser-compat.yml` that on every push to master (and every PR):
  1. Install Python deps, Playwright browsers
  2. Start `test_atlas_server.py` in background (`SITE_PASSWORD=""`, `PORT=8765`)
  3. Wait for `/health` to return 200
  4. Run `pytest tests/test_atlas_browser_compat.py --browser chromium --browser firefox --browser webkit -v`
  5. Upload `test-results/` artifact on failure (screenshots, traces)
  6. Job fails if any test fails
Cost: ~30 min. Catches every future "forgot to run tests" regression.

**Move 2 — Regression test for commit 027779c (risk-label clipping)**
Add `test_risk_label_not_clipped` to `tests/test_atlas_browser_compat.py`:
  - Open detail panel for any contractor
  - Get `.risk-label` computed `.height`, `.font-size`, bounding rect top vs `.risk-score-banner` top
  - Assert: height >= 15px (the real label is 16.5px; leaves Firefox slack), font-size == "11px", top distance from banner >= 10px
  - Assert: `getComputedStyle(riskScoreBanner, '::before').content === 'none'` (the pseudo-element that overlapped is gone)
Cost: 15 min.

**Move 3 — De-fragile the marker count assertion**
Replace `assert count == 2214` with `assert count >= 2200` (gives headroom for dataset growth; still catches catastrophic data loss).
Cost: 5 min.

**Move 4 — Rename / document `test_atlas_server.py`**
The file is the production entry but its name implies test-only. Two options:
  - (a) Rename to `server.py`, update Procfile/railway.toml/Dockerfile/tests that reference it
  - (b) Add a prominent header comment: `# NOTE: This file IS the production server (Railway/Dockerfile). The historical name is misleading.`

Going with (b) — (a) is a rename across 4 deploy files with nonzero risk of breaking the Railway deploy; (b) is a 3-line comment that prevents the next confusion.
Cost: 5 min.

**Move 5 — Self-host vendor JS + SRI for fonts**
Download Leaflet 1.9.4, MarkerCluster 1.5.3, leaflet.heat 0.2.0, d3 7.9.0 to `frontend/static/vendor/`. Update the `<script>` / `<link>` tags in `contractor-map.html` to load from `/static/vendor/...` instead of `unpkg.com`. Add `integrity` (SRI) + `crossorigin="anonymous"` attributes to the Google Fonts link.
Side effect: offline-capable after first load (except Google Fonts, which fall back to system monospace gracefully because `font-family` chains to `monospace`).
Risk: load-order assumptions in Leaflet plugins — MarkerCluster and leaflet.heat must load AFTER leaflet.js. Preserve order.
Regression test: `test_page_loads_without_errors` already covers the "no JS console errors on load" assertion.
Cost: 45 min.

**Move 6 — Client-side error telemetry (scope: A — full)**
Client side (in `contractor-map.html`):
  ```js
  (function setupErrorTelemetry() {
    const SESSION_ID = crypto.randomUUID?.() || String(Date.now());
    let rateLimit = 0;
    const RATE_LIMIT_PER_MIN = 10;
    setInterval(() => { rateLimit = 0; }, 60000);

    function report(kind, payload) {
      if (rateLimit >= RATE_LIMIT_PER_MIN) return;
      rateLimit++;
      try {
        fetch('/api/client-error', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            session: SESSION_ID,
            kind,
            url: location.href,
            userAgent: navigator.userAgent,
            viewport: [innerWidth, innerHeight],
            timestamp: new Date().toISOString(),
            ...payload,
          }),
          keepalive: true,
        }).catch(() => {});  // never let telemetry itself throw
      } catch (_) {}
    }

    window.addEventListener('error', (e) => {
      report('error', {message: e.message, source: e.filename, lineno: e.lineno, colno: e.colno, stack: e.error?.stack});
    });
    window.addEventListener('unhandledrejection', (e) => {
      report('unhandled_rejection', {reason: String(e.reason), stack: e.reason?.stack});
    });
  })();
  ```

Server side (in `test_atlas_server.py`):
  - Add `POST /api/client-error` endpoint, auth-protected by the same cookie (middleware already handles it)
  - Append validated JSON to `logs/client_errors.jsonl`
  - Rate-limit: max 60 requests/min per session (second line of defense beyond client-side limit)
  - Size limit: reject bodies > 8KB
  - Return 204 No Content

Regression test: A new Playwright test injects a thrown `Error`, then asserts the fetch was called. Mock the endpoint with `page.route()` and assert payload shape. (Does not need to hit a real backend during tests.)
Cost: 45 min.

**Move 7 — Extract textarea inline `onkeydown` handler (NARROWED)**
`contractor-map.html:2313` has an inline `onkeydown="..."` on the `#atlasChatInput` textarea. Move the handler into the existing JS section as a proper `addEventListener('keydown', ...)`, preserving the `isComposing` guard and shift-modifier handling.

**Why narrowed:** The full file contains 28 inline event handlers (verified by grep). The other 27 are mechanical `onclick="fn()"` calls — many generated dynamically inside JS template literals — and removing them is pure structural cleanup with no robustness or cross-browser benefit, while carrying nontrivial regression risk. The textarea handler is the *only* one with subtle browser-quirky behavior worth preserving in a real listener (CJK IME composition guard, shift-modifier branching).
Cost: 10 min.

**Move 8 — Responsive viewport sweep**
Parametrize the 3 most layout-sensitive tests (`test_legend_click_filters_markers_on_parent_div`, `test_risk_factors_have_readable_size`, `test_command_console_is_larger`) over viewports `[(1920,1080), (1366,768), (1280,720)]`. Use pytest parametrize with viewport set via `page.set_viewport_size()` in a fixture.
Cost: 30 min.

**Move 9 — Smoke-flow interaction sequence test**
New test `test_smoke_flow_no_console_errors`:
  1. Navigate to `/atlas`
  2. Click a marker cluster
  3. Click a legend item (filter)
  4. Open detail panel on a contractor
  5. Open the Command Console
  6. Type a query and press Enter (mocked API response)
  7. Close the console
  8. Assert NO console errors or unhandled rejections during the entire sequence
This turns the test suite from "state assertions" into actual user-flow coverage.
Cost: 30 min.

**Move 10 — CI inline-handler counter (warn-only baseline + ratchet)**
Add a CI step that counts inline event handlers in `contractor-map.html` and **fails the build only if the count INCREASES** above a recorded baseline. This is a "ratchet" guard — it doesn't force the existing 28 handlers to be removed today, but prevents any new ones from being added.

```yaml
- name: Inline event handler ratchet (no new inline handlers)
  run: |
    BASELINE=28  # current count as of 2026-04-07
    COUNT=$(grep -cE 'on(click|keydown|keyup|keypress|change|submit|input|focus|blur|load|mouseover|mouseout)="' frontend/static/contractor-map.html || true)
    echo "Inline handler count: $COUNT (baseline: $BASELINE)"
    if [ "$COUNT" -gt "$BASELINE" ]; then
      echo "::error::Inline event handler count increased from $BASELINE to $COUNT. Use addEventListener instead."
      grep -nE 'on(click|keydown|keyup|keypress|change|submit|input|focus|blur|load|mouseover|mouseout)="' frontend/static/contractor-map.html
      exit 1
    fi
```

**Why ratchet vs hard ban:** The full file currently contains 28 inline handlers. Removing them all is hours of careful refactoring (especially the 6+ generated dynamically inside template literals via `${idx}`) with regression risk and zero robustness benefit. The ratchet prevents the class from *growing*, gives us a leading defense against new ones, and lets us pay down the existing ones in future passes if we ever want to.

**Note on baseline coordination with Move 7:** Move 7 extracts the textarea `onkeydown`, dropping the count from 28 to 27. The Move 10 commit lands AFTER Move 7, so the baseline written into the workflow is **27**, not 28.
Cost: 15 min.

## Implementation order and commit grouping

Each move is independent, but there are two ordering constraints:
- Move 1 (CI) should land BEFORE Moves 2–10 so every subsequent move proves itself in CI
- Move 7 (extract inline handler) MUST land BEFORE Move 10 (lint guard), or the guard fails
- Move 5 (self-host vendor) should land AFTER Move 1 so CI catches any load-order breakage

Recommended commit sequence (one commit per move, or bundled as noted):
1. **Commit 1 — Baseline verification** (no code changes; just proves the 42-test suite passes right now)
2. **Commit 2 — CI + lint guard (without inline-handler check yet)** (Moves 1 + initial .yml)
3. **Commit 3 — Test hygiene**: regression test for 027779c, marker count fix, rename comment (Moves 2 + 3 + 4)
4. **Commit 4 — Self-host vendor JS + SRI** (Move 5)
5. **Commit 5 — Client error telemetry** (Move 6, client + server + test)
6. **Commit 6 — Extract inline handler + enable CI lint guard** (Moves 7 + 10 together, so the guard is enabled the same commit the last inline handler dies)
7. **Commit 7 — Responsive viewport sweep + smoke flow test** (Moves 8 + 9)

7 commits. Each independently revertable. Each runs CI. Each has a clear name.

## Testing strategy

**Baseline (before any change):** Run the existing 42-test suite against `test_atlas_server.py`. Record the starting count. **If not 42/42 green, stop and diagnose.** This is the VALIDATE gate for Task 0.

**Per-commit:** Every commit must leave the suite green. This is the integration check after each move.

**Final VALIDATE gate:** Run the full suite (which by then includes new tests from Moves 2, 6, 8, 9) in all 3 browsers. Expected delta:
- +1 unique function for Move 2 (risk label regression)
- +1 unique function for Move 6 (telemetry)
- +1 unique function for Move 9 (smoke flow)
- Move 8 parametrizes 3 existing functions over 3 viewports — adds 3×(3−1) = 6 additional test items (each parametrized function generates 3 items instead of 1)

Starting from 14 unique test items, the suite grows to ~14 + 3 (new functions) + 6 (parametrize delta) = **23 unique test items × 3 browsers = ~69 executions** at the final gate. Report the actual count from pytest output, not the predicted count.

**Manual spot check:** Load `/atlas` in local Chrome, Firefox, Safari once per commit that touches `contractor-map.html`. Five minutes per commit, documented in commit message.

## Success criteria

1. Baseline: 42/42 tests pass before any change
2. After Move 1: `.github/workflows/browser-compat.yml` exists and runs green on push
3. After Move 2: new `test_risk_label_not_clipped` passes in all 3 browsers
4. After Move 3: no `assert count == 2214` anywhere in the suite
5. After Move 4: `test_atlas_server.py` has a prominent header comment documenting its production role
6. After Move 5: `contractor-map.html` references `/static/vendor/` for Leaflet/MarkerCluster/heat/d3; `page.goto('/atlas')` works with `unpkg.com` added to a hosts-file blackhole
7. After Move 6: throwing a JS error in the page causes a row to land in `logs/client_errors.jsonl`; telemetry test asserts payload shape
8. After Move 7: no inline `on[a-z]+=` attributes in `frontend/static/contractor-map.html`
9. After Move 8: each parametrized viewport test runs once per viewport per browser; all pass
10. After Move 9: `test_smoke_flow_no_console_errors` drives 7 interactions and asserts zero console errors
11. After Move 10: CI lint guard step reports "no inline handlers found" (green)
12. **Final gate**: Full suite ≥54 tests, ALL pass on chromium + firefox + webkit

## Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Baseline suite fails before any change | L | H | Task 0 detects this; we stop and diagnose before any other work |
| Self-hosting vendor JS breaks Leaflet plugin load order | M | H | Preserve script tag order; test_page_loads_without_errors catches it; rollback is one-commit revert |
| CI workflow consumes GitHub Actions minutes | L | L | Single workflow, runs only on master pushes + PRs; Playwright binaries cached |
| Telemetry endpoint abused (write spam) | L | M | Client-side rate limit + server-side rate limit + 8KB body size limit + auth-cookie gate |
| Responsive viewport tests reveal layout bugs at 1366×768 | M | M | *This is the point.* If bugs are revealed, they become followup commits — not blockers for this design. |
| Extracting inline handler regresses the textarea Enter behavior | L | M | Test `test_textarea_auto_grows_on_multiline_input` already exists; add an Enter-key test if none exists |
| Inline-handler CI lint guard fires on legitimate attributes like `onclick` in docs/comments | L | L | Scope grep to only code outside comments, or use a more precise regex. If noise, relax to HTML element attributes only |

## Rollback

Each commit is independent and revertable. The riskiest commit is Move 5 (self-host vendor) — if it breaks production, `git revert` restores the unpkg CDN references. CI will catch this before merge.

## Open questions (none blocking)

None. The user picked telemetry scope A (full). All other decisions were self-resolvable from the codebase.
