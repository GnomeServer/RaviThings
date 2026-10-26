# Cross-Platform QA Strategy for OSINT Atlas

**Problem statement:** Almost every bug report we've gotten lately has been a "works on my machine" cross-browser or cross-platform issue. The developer (macOS, Chrome) doesn't see them; users on Windows + Firefox do. This document is the strategy to **catch them before users hit them**.

## Browser Support Matrix

| Browser | Engine | Tier | Notes |
|---------|--------|------|-------|
| Chrome (latest 2) | Chromium | **Tier 1** | Primary dev browser. Must work flawlessly. |
| Edge (latest 2) | Chromium | **Tier 1** | Same engine as Chrome — covered by Chromium tests. |
| Firefox (latest 2) | Gecko | **Tier 1** | Most users hit Firefox-specific quirks. Auto-tested. |
| Safari macOS (16+) | WebKit | **Tier 1** | Auto-tested via Playwright WebKit. |
| Safari iOS (15.4+) | WebKit | **Tier 2** | Engine matches; soft keyboard / touch needs manual check. |
| Edge Legacy / IE11 | EdgeHTML / Trident | **Unsupported** | Modern features (`AbortController`, `fetch`, optional chaining) won't work. |

The "Tier 1" browsers cover **>95% of real users** for an internal analyst tool. We test all four engine families on every commit that touches the frontend.

## The Three-Layer Defense

### Layer 1 — Automated cross-browser tests (Playwright)

**File:** `tests/test_atlas_browser_compat.py`

**Engines tested:** Chromium, Firefox, WebKit (one binary each — no real device farm needed).

**How to run:**
```bash
# One-time install
pip install playwright pytest-playwright
python3 -m playwright install chromium firefox webkit

# Start the local server in another terminal
PORT=8765 SITE_PASSWORD="" python3 test_atlas_server.py

# Run all tests against all three engines
python3 -m pytest tests/test_atlas_browser_compat.py \
    --browser chromium --browser firefox --browser webkit -v
```

**What it catches:**
- JavaScript API differences (e.g., the Firefox SVG hit-test bug)
- CSS rendering differences (e.g., text clipping due to font metrics)
- Layout differences (e.g., panel widths, button sizes)
- Functional regressions across browsers (e.g., a fix that works in Chrome breaking Firefox)

**What it doesn't catch:**
- iOS Safari soft keyboard layout (no real device)
- Touch input vs click input (Playwright simulates clicks)
- Real LLM responses (we mock fetch)

### Layer 2 — Defensive coding patterns

These are the patterns we use to make code work across browsers without hoping for the best:

1. **CSS vendor prefixes for non-standard properties.** Always include `-webkit-backdrop-filter` alongside `backdrop-filter`. Use [Can I Use](https://caniuse.com) before adopting a new property.
2. **Feature detection in JS.** Check `if (!response.body)` before calling `.getReader()`. Check `typeof crypto.randomUUID === 'function'` before calling it.
3. **`pointer-events: none` on click target children.** When a parent should be clickable, force its children to be transparent to clicks. This is the canonical fix for SVG/child-element click bubbling issues across browsers.
4. **Event delegation as a safety net.** Even with pointer-events, attach the click listener to the parent container (`#legendItems`) and use `e.target.closest('.legend-item')` to find the right item. Two-layer redundancy.
5. **`100dvh` with `100vh` fallback** for any full-height element. iOS Safari includes the URL bar in `100vh`, breaking layouts when the soft keyboard opens.
6. **`isComposing` guards** on Enter-key handlers. Asian (CJK) IMEs fire `keydown` Enter mid-composition. Without the guard, half-typed text submits.
7. **Touch targets >= 44×44px** for any tappable element. iOS Human Interface Guidelines require this for accessibility.
8. **Stable DOM children for streaming updates.** When you stream content into an element, use multiple stable child nodes (`.assistant-text` + `.assistant-badges`) so updates to one don't wipe the other. Avoid `innerHTML +=` patterns.

### Layer 3 — Pre-deploy verification

Before any commit that touches `frontend/static/contractor-map.html`:

1. **Run the Python parser tests:** `python3 tests/test_atlas_parser.py`
2. **Start the server and run the browser compat suite:**
   ```bash
   PORT=8765 SITE_PASSWORD="" python3 test_atlas_server.py &
   python3 -m pytest tests/test_atlas_browser_compat.py \
       --browser chromium --browser firefox --browser webkit -v
   kill %1
   ```
3. **Manually click through** the new code in at least one non-Chrome browser locally. Five minutes saves five hours of "works on my machine" debugging.
4. **For Bug 2 / typography style changes:** also visually verify on a 1920×1080 Windows display if you have access. Font rendering differs from macOS Retina.

## Adding a New Test

When you fix a cross-browser bug, **add a regression test to `test_atlas_browser_compat.py` for it** before merging. The pattern:

```python
def test_my_bug_fix(page: Page):
    """One-line description of what the bug was and what this verifies."""
    result = page.evaluate("""() => {
        // Reproduce the buggy scenario
        // Return state we can assert against
    }""")
    assert result["expected_property"] == expected_value, f"got {result}"
```

Every test runs three times (one per browser engine) with no extra effort. If you add a Firefox-specific test, you'll know within seconds if the fix also works in Chromium and WebKit.

## CI/CD Future Work

This strategy is currently **manual-run-before-commit**. To make it bulletproof:

1. **GitHub Actions workflow** that runs the browser compat suite on every PR. Block merges on test failure.
2. **Visual regression with Percy or Playwright snapshots** to catch unintended layout changes.
3. **Real device cloud (BrowserStack)** for iOS Safari touch testing if mobile becomes a tier-1 target.
4. **Lighthouse CI** for performance + accessibility scores.

None of these are blockers — the local Playwright suite already catches the vast majority of cross-platform issues.

## Bug Report Triage Checklist

When a user reports a bug we can't reproduce:

1. **Ask for browser + OS + version.** Not optional.
2. **Ask for a screenshot.** Layout issues are obvious from a screenshot but invisible from a description.
3. **Ask for the browser console output.** `Cmd+Option+J` (Chrome/Firefox), `Cmd+Option+I` (Safari).
4. **Try to reproduce in the matching browser locally** via Playwright before assuming it's environmental.
5. **If reproduced:** add a test to the compat suite, then fix.
6. **If not reproduced after 15 minutes:** ask the user to record their screen with the dev console open. Don't speculate.

The goal is to convert "users on my system have a bug" from a guessing game into a binary signal: either the test fails on Firefox/WebKit (and we have evidence to fix) or it passes everywhere (and we ask for more user-side data).
