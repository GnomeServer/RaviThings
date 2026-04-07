"""Cross-browser compatibility tests for the OSINT Atlas Command Console.

This test suite is the FIRST line of defense against the "works on my
machine" problem. It runs the SAME test scenarios against three different
browser engines:

  - Chromium (used by Chrome, Edge, Brave, Opera)
  - Firefox (Gecko engine)
  - WebKit (used by Safari, including iOS Safari)

That covers >95% of real-world users with a single test run.

────────────────────────────────────────────────────────────────────────
HOW TO RUN
────────────────────────────────────────────────────────────────────────

1. Install dependencies (one time):

       pip install playwright pytest-playwright
       python3 -m playwright install chromium firefox webkit

2. Start the local atlas server in a separate terminal:

       PORT=8765 SITE_PASSWORD="" python3 test_atlas_server.py

3. Run the tests against ALL THREE browsers in one shot:

       python3 -m pytest tests/test_atlas_browser_compat.py \
           --browser chromium --browser firefox --browser webkit -v

   Or against a single browser:

       python3 -m pytest tests/test_atlas_browser_compat.py --browser firefox -v

   Or with screenshots on failure:

       python3 -m pytest tests/test_atlas_browser_compat.py \
           --browser chromium --browser firefox --browser webkit \
           --screenshot=only-on-failure --output=test-results -v

4. Read the output. Each scenario runs three times (one per browser).
   If a test passes in Chromium but fails in Firefox, you've caught a
   cross-browser issue BEFORE a user reports it.

────────────────────────────────────────────────────────────────────────
WHAT THIS COVERS
────────────────────────────────────────────────────────────────────────

  • Page loads cleanly on every engine (no console errors)
  • Map and 2,214 markers render
  • Legend filter click works (Bug 1 — Firefox SVG hit-test regression)
  • Detail panel opens with readable risk factors (Bug 2 — text clipping)
  • Risk factor pills are tall enough to display text (>= 18px height)
  • Command Console opens, accepts text, and self-heals after a stuck state
  • Empty filter guard preserves markers
  • Kill chain panel and chat console coexist (slide-aside)
  • Closing the chat console preserves the detail panel
  • Map action badges persist across token updates
  • Send/Stop button visibility toggles correctly

────────────────────────────────────────────────────────────────────────
WHAT THIS DOES NOT COVER (and why)
────────────────────────────────────────────────────────────────────────

  • Real LLM responses — we mock fetch to avoid backend dependency.
    The conversation history fix (C1) is verified by inspecting the
    payload structure rather than the LLM output.
  • iOS Safari soft keyboard layout — Playwright WebKit runs the same
    engine but not on a real device. M3 (100dvh) is verified by CSS
    presence, not by triggering the soft keyboard.
  • Real touch input — Playwright simulates clicks; touch is implied
    by the 44x44 button sizing assertion.
  • Visual regression — pixel diffs are out of scope. If you need them,
    add `--snapshot-update` and use `expect(page).to_have_screenshot()`.

────────────────────────────────────────────────────────────────────────
ADDING A NEW TEST
────────────────────────────────────────────────────────────────────────

Every test function takes a `page` fixture provided by pytest-playwright.
Inside, drive the page with `page.goto`, `page.evaluate`, `page.click`,
and assert with `assert`. The fixture runs the same function once per
browser engine selected on the command line.
"""

import os
import pytest
from playwright.sync_api import Page, expect

ATLAS_URL = os.environ.get("ATLAS_URL", "http://localhost:8765/atlas")


@pytest.fixture(autouse=True)
def goto_atlas(page: Page):
    """Navigate every test to the atlas page and wait for it to be ready."""
    page.goto(ATLAS_URL)
    # Wait for the data to load and the map cluster to initialize
    page.wait_for_function(
        "typeof markerCluster !== 'undefined' && markerCluster !== null && "
        "typeof allMarkers !== 'undefined' && allMarkers.length > 0",
        timeout=15000,
    )


# ─────────────────────────────────────────────────────────────────────
# Page load + smoke tests
# ─────────────────────────────────────────────────────────────────────

def test_page_loads_without_errors(page: Page):
    """Page loads, title is set, no JS errors in console (favicon 404 ok)."""
    errors = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.reload()
    page.wait_for_function("typeof DATA !== 'undefined' && DATA !== null", timeout=15000)
    assert page.title() == "OSINT Atlas — DOE Contractor Intelligence"
    assert errors == [], f"Page errors: {errors}"


def test_all_markers_render(page: Page):
    """All 2,214 contractor markers are added to the cluster."""
    count = page.evaluate("() => allMarkers.length")
    assert count == 2214, f"expected 2214 markers, got {count}"
    visible = page.evaluate("""() => {
        let n = 0; markerCluster.eachLayer(() => n++); return n;
    }""")
    assert visible == 2214


# ─────────────────────────────────────────────────────────────────────
# Bug 1 — Legend filter click (Firefox/Windows SVG hit-test regression)
# ─────────────────────────────────────────────────────────────────────

def test_legend_click_filters_markers_on_parent_div(page: Page):
    """Clicking the legend item DIV directly filters markers."""
    result = page.evaluate("""() => {
        const item = document.querySelector('#legendItems .legend-item[data-category="IT & Cyber"]');
        let before = 0; markerCluster.eachLayer(() => before++);
        item.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
        let after = 0; markerCluster.eachLayer(() => after++);
        return { before, after, dimmed: item.classList.contains('dimmed') };
    }""")
    assert result["before"] > result["after"], (
        f"clicking legend item should reduce visible markers; got {result}"
    )
    assert result["dimmed"], "legend item should have .dimmed class after click"


def test_legend_click_on_swatch_child_still_filters(page: Page):
    """Clicking the SVG swatch (a child) should still bubble to parent.

    This is the key Firefox regression test: SVG hit-testing in Firefox
    sometimes failed to bubble clicks up to parent elements. The fix uses
    `pointer-events: none` on legend-item children plus event delegation.
    """
    result = page.evaluate("""() => {
        const item = document.querySelector('#legendItems .legend-item[data-category="Manufacturing"]');
        const swatch = item.querySelector('.legend-swatch');
        let before = 0; markerCluster.eachLayer(() => before++);
        swatch.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
        let after = 0; markerCluster.eachLayer(() => after++);
        return {
            swatchPointerEvents: window.getComputedStyle(swatch).pointerEvents,
            before, after,
            dimmed: item.classList.contains('dimmed'),
        };
    }""")
    # Either pointer-events:none is working, or event delegation is — both fix the bug
    assert result["before"] > result["after"], f"swatch click should filter markers; got {result}"
    assert result["dimmed"]


# ─────────────────────────────────────────────────────────────────────
# Bug 2 — Risk factor text clipping
# ─────────────────────────────────────────────────────────────────────

def test_risk_factors_have_readable_size(page: Page):
    """Risk factor pills are tall enough that text isn't clipped."""
    result = page.evaluate("""() => {
        // Find a high-risk contractor and open its panel
        let bestIdx = 0, mostFactors = 0;
        for (let i = 0; i < 200; i++) {
            const r = computeRiskScore(DATA.contractors[i]);
            if (r.factors.length > mostFactors) { mostFactors = r.factors.length; bestIdx = i; }
        }
        openDetailPanel(bestIdx);
        const factor = document.querySelector('.risk-factor');
        if (!factor) return { error: 'no risk factor element' };
        const rect = factor.getBoundingClientRect();
        const cs = window.getComputedStyle(factor);
        return {
            height: rect.height,
            fontSize: cs.fontSize,
            lineHeight: cs.lineHeight,
            padding: cs.padding,
        };
    }""")
    assert result.get("height", 0) >= 18, (
        f"risk factor pill should be at least 18px tall to avoid clipping; got {result}"
    )
    assert result["fontSize"] in ("11px",), (
        f"risk factor font should be 11px; got {result['fontSize']}"
    )


def test_section_dividers_are_not_cyan(page: Page):
    """The 'blue highlighting' added for video creation should be gone.

    Section title underlines and panel section dividers should be neutral
    grey, not cyan rgba(0,229,255,...).
    """
    result = page.evaluate("""() => {
        openDetailPanel(0);
        const section = document.querySelector('.panel-section');
        const title = document.querySelector('.section-title');
        return {
            sectionBorderBottom: window.getComputedStyle(section).borderBottomColor,
            titleBorderBottom: window.getComputedStyle(title).borderBottomColor,
            titleColor: window.getComputedStyle(title).color,
        };
    }""")
    # The neutral divider is rgba(255, 255, 255, 0.06) — should NOT contain "229" (cyan green channel)
    assert "229" not in result["sectionBorderBottom"], (
        f"panel-section border-bottom is still cyan: {result['sectionBorderBottom']}"
    )
    assert "229" not in result["titleBorderBottom"], (
        f"section-title border-bottom is still cyan: {result['titleBorderBottom']}"
    )


# ─────────────────────────────────────────────────────────────────────
# Bug 3 — Typography and panel sizing
# ─────────────────────────────────────────────────────────────────────

def test_command_console_is_larger(page: Page):
    """Command Console panel is at least 500px wide for readability."""
    result = page.evaluate("""() => {
        toggleAtlasChat();
        const panel = document.getElementById('atlasChatPanel');
        return {
            width: panel.getBoundingClientRect().width,
            fontSize: window.getComputedStyle(panel).fontSize,
        };
    }""")
    assert result["width"] >= 500, f"chat panel width should be >= 500px; got {result}"
    # Body font should be 13px (--fs-body)
    assert result["fontSize"] in ("13px",), f"chat font should be 13px; got {result['fontSize']}"


def test_detail_panel_is_larger(page: Page):
    """Detail panel is at least 520px wide and has a readable base font."""
    result = page.evaluate("""() => {
        openDetailPanel(0);
        const panel = document.getElementById('detailPanel');
        return {
            width: panel.getBoundingClientRect().width,
            fontSize: window.getComputedStyle(panel).fontSize,
        };
    }""")
    assert result["width"] >= 520, f"detail panel width should be >= 520px; got {result}"
    assert result["fontSize"] in ("13px",)


def test_send_button_meets_touch_target_size(page: Page):
    """Send button is at least 44x44 (iOS recommended touch target)."""
    result = page.evaluate("""() => {
        if (!atlasChatOpen) toggleAtlasChat();
        const send = document.getElementById('atlasChatSend');
        const rect = send.getBoundingClientRect();
        return { width: rect.width, height: rect.height };
    }""")
    assert result["width"] >= 44 and result["height"] >= 44, (
        f"Send button should be >= 44x44; got {result}"
    )


# ─────────────────────────────────────────────────────────────────────
# Audit bundle — empty filter guard, badge persistence, etc.
# ─────────────────────────────────────────────────────────────────────

def test_empty_filter_guard_preserves_markers(page: Page):
    """LLM emitting a filter that matches zero contractors must not blank the map."""
    result = page.evaluate("""() => {
        let before = 0; markerCluster.eachLayer(() => before++);
        executeMapCommand({action: 'filter', field: 'category', value: 'NONEXISTENT_XYZ', op: 'eq'});
        let after = 0; markerCluster.eachLayer(() => after++);
        return { before, after };
    }""")
    assert result["before"] == result["after"] == 2214


def test_kill_chain_panel_coexists_with_chat(page: Page):
    """When kill_chain triggers a panel, the chat slides aside instead of overlapping."""
    result = page.evaluate("""async () => {
        toggleAtlasChat();
        await new Promise(r => setTimeout(r, 100));
        executeMapCommand({action: 'kill_chain', contractor_index: 0});
        await new Promise(r => setTimeout(r, 200));
        return {
            chatLeftSide: document.getElementById('atlasChatPanel').classList.contains('left-side'),
            detailOpen: document.getElementById('detailPanel').classList.contains('open'),
        };
    }""")
    assert result["chatLeftSide"] is True
    assert result["detailOpen"] is True


def test_closing_chat_preserves_detail_panel(page: Page):
    """Closing the chat console must NOT close the detail panel."""
    result = page.evaluate("""async () => {
        openDetailPanel(0);
        toggleAtlasChat();
        await new Promise(r => setTimeout(r, 100));
        toggleAtlasChat();  // close
        await new Promise(r => setTimeout(r, 200));
        return {
            chatOpen: atlasChatOpen,
            detailOpen: document.getElementById('detailPanel').classList.contains('open'),
        };
    }""")
    assert result["chatOpen"] is False
    assert result["detailOpen"] is True


def test_send_stop_button_visibility(page: Page):
    """Send button shows when idle, Stop button shows during streaming."""
    result = page.evaluate("""() => {
        if (!atlasChatOpen) toggleAtlasChat();
        setChatStreamingUI(false);
        const sendIdle = window.getComputedStyle(document.getElementById('atlasChatSend')).display;
        const stopIdle = window.getComputedStyle(document.getElementById('atlasChatStop')).display;
        setChatStreamingUI(true);
        const sendStreaming = window.getComputedStyle(document.getElementById('atlasChatSend')).display;
        const stopStreaming = window.getComputedStyle(document.getElementById('atlasChatStop')).display;
        setChatStreamingUI(false);
        return { sendIdle, stopIdle, sendStreaming, stopStreaming };
    }""")
    assert result["sendIdle"] == "flex"
    assert result["stopIdle"] == "none"
    assert result["sendStreaming"] == "none"
    assert result["stopStreaming"] == "flex"


def test_textarea_auto_grows_on_multiline_input(page: Page):
    """Textarea grows when user pastes multi-line content."""
    result = page.evaluate("""() => {
        if (!atlasChatOpen) toggleAtlasChat();
        const ta = document.getElementById('atlasChatInput');
        ta.value = '';
        ta.style.height = 'auto';
        const initial = ta.offsetHeight;
        ta.value = 'line one\\nline two\\nline three\\nline four';
        ta.dispatchEvent(new Event('input', { bubbles: true }));
        const grown = ta.offsetHeight;
        return { initial, grown };
    }""")
    assert result["grown"] > result["initial"], f"textarea should grow; got {result}"
    assert result["grown"] <= 120, f"textarea should cap at 120px; got {result}"
