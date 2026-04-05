"""Visual transition helpers for video recording.

All effects are injected as JavaScript via Playwright's page.evaluate().
No frontend code changes required. Matches the tactical HUD aesthetic
(dark navy, JetBrains Mono, cyan accent).
"""
import time


def wait(seconds):
    """Sleep for the given number of seconds."""
    time.sleep(seconds)


def inject_transition_styles(page):
    """Inject the CSS needed for all transitions. Call once after page load."""
    page.evaluate("""() => {
        if (document.getElementById('video-transition-styles')) return;
        const style = document.createElement('style');
        style.id = 'video-transition-styles';
        style.textContent = `
            #video-fade-overlay {
                position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
                background: #0a0e1a; z-index: 99999; pointer-events: none;
                opacity: 0; transition: opacity 0.8s ease-in-out;
            }
            #video-title-card {
                position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
                background: linear-gradient(180deg, #080c18 0%, #0a0e1a 40%, #0d1225 100%);
                z-index: 100000; pointer-events: none;
                display: flex; flex-direction: column; align-items: center;
                justify-content: center; opacity: 0;
                transition: opacity 0.8s ease-in-out;
                font-family: 'JetBrains Mono', monospace;
            }
            #video-title-card .tc-label {
                color: #00e5ff; font-size: 14px; letter-spacing: 8px;
                text-transform: uppercase; margin-bottom: 20px;
                opacity: 0.8;
            }
            #video-title-card .tc-title {
                color: #e0e6ed; font-size: 38px; letter-spacing: 6px;
                text-transform: uppercase; font-weight: 700;
                text-shadow: 0 0 30px rgba(0, 229, 255, 0.15);
            }
            #video-title-card .tc-subtitle {
                color: #8899aa; font-size: 16px; margin-top: 16px;
                font-family: 'Outfit', sans-serif; letter-spacing: 1px;
            }
            #video-title-card .tc-line {
                width: 60px; height: 1px; background: #00e5ff;
                margin: 24px 0; opacity: 0.5;
            }
            .highlight-pulse {
                animation: vpHighlightPulse 2s ease-in-out !important;
            }
            @keyframes vpHighlightPulse {
                0%   { box-shadow: inset 3px 0 0 #00e5ff; }
                50%  { box-shadow: inset 3px 0 0 #00e5ff, 0 0 25px rgba(0,229,255,0.25); }
                100% { box-shadow: inset 3px 0 0 transparent; }
            }
        `;
        document.head.appendChild(style);

        // Create fade overlay
        const fade = document.createElement('div');
        fade.id = 'video-fade-overlay';
        document.body.appendChild(fade);

        // Create title card
        const card = document.createElement('div');
        card.id = 'video-title-card';
        card.innerHTML = `
            <div class="tc-label"></div>
            <div class="tc-title"></div>
            <div class="tc-line"></div>
            <div class="tc-subtitle"></div>
        `;
        document.body.appendChild(card);
    }""")


def fade_to_black(page, duration_ms=800):
    """Fade the screen to black."""
    page.evaluate("""(ms) => {
        const el = document.getElementById('video-fade-overlay');
        el.style.transition = `opacity ${ms}ms ease-in-out`;
        el.style.opacity = '1';
    }""", duration_ms)
    wait(duration_ms / 1000 + 0.2)


def fade_from_black(page, duration_ms=800):
    """Fade from black to reveal the screen."""
    page.evaluate("""(ms) => {
        const el = document.getElementById('video-fade-overlay');
        el.style.transition = `opacity ${ms}ms ease-in-out`;
        el.style.opacity = '0';
    }""", duration_ms)
    wait(duration_ms / 1000 + 0.2)


def show_title_card(page, label, title, subtitle="", hold_sec=2.0):
    """Show a full-screen title card with label, title, and optional subtitle."""
    # Escape single quotes for JS string safety
    label = label.replace("'", "\\'")
    title = title.replace("'", "\\'")
    subtitle = subtitle.replace("'", "\\'")

    page.evaluate(f"""() => {{
        const card = document.getElementById('video-title-card');
        card.querySelector('.tc-label').textContent = '{label}';
        card.querySelector('.tc-title').textContent = '{title}';
        card.querySelector('.tc-subtitle').textContent = '{subtitle}';
        card.style.opacity = '1';
    }}""")
    wait(0.8 + hold_sec)  # fade-in + hold
    page.evaluate("""() => {
        document.getElementById('video-title-card').style.opacity = '0';
    }""")
    wait(1.0)  # fade-out


def smooth_scroll_to(page, panel_selector, target_text, duration_ms=1000):
    """Smoothly scroll a panel until an element containing target_text is visible."""
    page.evaluate("""([sel, text]) => {
        const panel = document.querySelector(sel);
        if (!panel) return;
        // Search section titles and first-child divs
        const candidates = panel.querySelectorAll(
            '.section-title, .panel-section > div:first-child, h3, h4'
        );
        for (const el of candidates) {
            if (el.textContent.includes(text)) {
                el.scrollIntoView({ behavior: 'smooth', block: 'start' });
                return;
            }
        }
        // Fallback: search all text nodes
        const all = panel.querySelectorAll('*');
        for (const el of all) {
            if (el.children.length === 0 && el.textContent.includes(text)) {
                el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                return;
            }
        }
    }""", [panel_selector, target_text])
    wait(duration_ms / 1000 + 0.5)


def smooth_scroll_panel(page, panel_selector, pixels, steps=10):
    """Smoothly scroll a panel by a given number of pixels in incremental steps."""
    step_size = pixels // steps
    for _ in range(steps):
        page.evaluate("""([sel, px]) => {
            const panel = document.querySelector(sel);
            if (panel) panel.scrollTop += px;
        }""", [panel_selector, step_size])
        wait(0.06)
    wait(0.3)


def highlight_section(page, section_text, duration_ms=2000):
    """Add a brief cyan glow to a panel section containing the given text."""
    page.evaluate("""([text, ms]) => {
        const sections = document.querySelectorAll('.panel-section');
        for (const s of sections) {
            const title = s.querySelector('.section-title');
            if (title && title.textContent.includes(text)) {
                s.classList.add('highlight-pulse');
                setTimeout(() => s.classList.remove('highlight-pulse'), ms);
                return;
            }
        }
    }""", [section_text, duration_ms])
    wait(0.3)


def cinematic_fly(page, lat, lon, zoom, duration_sec=2.5):
    """Smoothly fly the Leaflet map to a location with a slow ease.

    Note: The frontend declares `let map` at script top-level, which is
    accessible in page.evaluate() but NOT as window.map.
    """
    page.evaluate("""([lat, lon, z, dur]) => {
        // 'map' is a top-level let binding, accessible directly (not on window)
        if (typeof map !== 'undefined' && map && map.flyTo) {
            map.flyTo([lat, lon], z, { duration: dur, easeLinearity: 0.25 });
        }
    }""", [lat, lon, zoom, duration_sec])
    wait(duration_sec + 0.5)


def type_slowly(page, selector, text, delay_ms=50):
    """Type text character by character into an input element."""
    el = page.locator(selector)
    el.click()
    el.fill("")
    for char in text:
        el.type(char, delay=delay_ms)
