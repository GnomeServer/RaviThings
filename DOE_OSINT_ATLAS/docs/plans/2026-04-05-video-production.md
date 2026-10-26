# Video Production Pipeline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a polished ~11min technical briefing video with Brian voiceover synced to choreographed UI layer demonstrations with smooth visual transitions.

**Architecture:** Strip section headers from narration → regenerate audio via single ElevenLabs call → record single continuous Playwright take with JS-injected transitions → ffmpeg merge.

**Tech Stack:** ElevenLabs Python SDK v2.41.0, Playwright v1.58.0, ffmpeg, Python 3.12

---

### Task 1: Create TTS-Ready Narration

**Files:**
- Create: `videos/combined_narration_tts.txt`
- Read: `videos/combined_narration.txt`

**Ground Truth:** ElevenLabs TTS reads all text verbatim including brackets. Section headers must be stripped.

**Provides:** `videos/combined_narration_tts.txt` — clean narration text suitable for TTS

- [ ] **Step 1: Create the TTS-ready narration**

Strip these patterns from `combined_narration.txt`:
- `[SECTION 1 — SITUATION]` → replace with `(pause)`
- `[SECTION 2 — KEY FINDINGS]` → replace with `Key findings.` + blank line
- `[SECTION 3 — ATTACK PATH ANALYSIS]` → replace with `Attack path analysis.` + blank line
- `[SECTION 4 — FINDING OF NOTE: MANAGEMENT COMPANY EMAIL AUTHENTICATION]` → replace with `A finding of note. Management company email authentication.` + blank line
- `[CLOSE]` → remove entirely (the closing paragraph flows naturally)
- Keep the header lines (title, classification, sources) — those set the tone
- Remove the `OSINT ATLAS:` title line — it's visual, not spoken

- [ ] **Step 2: Verify the file**

```bash
wc -c videos/combined_narration_tts.txt
# Should be ~8200-8500 chars (slightly different from original)
python3 -c "t=open('videos/combined_narration_tts.txt').read(); print(f'{len(t)} chars'); assert '[SECTION' not in t; assert '[CLOSE]' not in t; print('No brackets found - OK')"
```

- [ ] **Step 3: Commit**

```bash
git add videos/combined_narration_tts.txt
git commit -m "docs: TTS-ready narration with section headers stripped"
```

---

### Task 2: Update Audio Generation Script

**Files:**
- Modify: `generate_voiceover.py`

**Ground Truth:** ElevenLabs Pro plan supports 50,000 chars/request. SDK v2.41.0 `client.text_to_speech.convert(voice_id, *, text=, model_id=, output_format=)` returns `Iterator[bytes]`.

**Requires:** Task 1 (`videos/combined_narration_tts.txt`)
**Provides:** Updated `generate_voiceover.py` that reads TTS-ready text, generates in single call

- [ ] **Step 1: Update NARRATIONS dict to read TTS file**

Change the `"combined"` entry to read from `combined_narration_tts.txt` instead of `combined_narration.txt`.

- [ ] **Step 2: Increase MAX_CHARS to 50000**

Change `MAX_CHARS = 4500` to `MAX_CHARS = 50000` so the full narration goes in a single API call.

- [ ] **Step 3: Test audio generation**

```bash
python3 generate_voiceover.py --video combined --audio-only
# Expected: single chunk, generates videos/audio/osint_atlas_briefing.mp3
```

Verify:
```bash
ffprobe -v quiet -show_entries format=duration -of csv=p=0 videos/audio/osint_atlas_briefing.mp3
# Should be ~10-11 minutes (600-660 seconds)
ls -la videos/audio/osint_atlas_briefing.mp3
# Should be ~10MB for 128kbps MP3
```

- [ ] **Step 4: Commit**

```bash
git add generate_voiceover.py
git commit -m "feat: single-call audio generation for upgraded ElevenLabs plan"
```

---

### Task 3: Build Visual Transition Helpers

**Files:**
- Create: `video_transitions.py`

**Ground Truth:** Playwright `page.evaluate(js_string)` executes arbitrary JS in page context. Returns when Promise resolves. CSS transitions/animations work in Chromium.

**Provides:** Python module with `fade_to_black()`, `fade_from_black()`, `show_title_card()`, `smooth_scroll_to()`, `highlight_section()`, `cinematic_fly()` — all using `page.evaluate()`

- [ ] **Step 1: Create video_transitions.py with all helper functions**

```python
"""Visual transition helpers for video recording.

All effects are injected as JavaScript via Playwright's page.evaluate().
No frontend code changes required.
"""
import time


def wait(seconds):
    """Sleep for the given number of seconds."""
    time.sleep(seconds)


def inject_transition_styles(page):
    """Inject the CSS needed for transitions (call once at start)."""
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
                background: #0a0e1a; z-index: 100000; pointer-events: none;
                display: flex; flex-direction: column; align-items: center;
                justify-content: center; opacity: 0;
                transition: opacity 0.8s ease-in-out;
                font-family: 'JetBrains Mono', monospace;
            }
            #video-title-card .section-label {
                color: #00e5ff; font-size: 14px; letter-spacing: 8px;
                text-transform: uppercase; margin-bottom: 16px;
            }
            #video-title-card .section-title {
                color: #e0e6ed; font-size: 36px; letter-spacing: 4px;
                text-transform: uppercase; font-weight: 700;
            }
            #video-title-card .section-subtitle {
                color: #8899aa; font-size: 16px; margin-top: 12px;
                font-family: 'Outfit', sans-serif;
            }
            .highlight-pulse {
                animation: highlightPulse 2s ease-in-out;
            }
            @keyframes highlightPulse {
                0% { box-shadow: inset 3px 0 0 #00e5ff; }
                50% { box-shadow: inset 3px 0 0 #00e5ff, 0 0 20px rgba(0,229,255,0.3); }
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
        card.innerHTML = '<div class="section-label"></div><div class="section-title"></div><div class="section-subtitle"></div>';
        document.body.appendChild(card);
    }""")


def fade_to_black(page, duration_ms=800):
    """Fade the screen to black."""
    page.evaluate(f"""() => {{
        const el = document.getElementById('video-fade-overlay');
        el.style.transition = 'opacity {duration_ms}ms ease-in-out';
        el.style.opacity = '1';
    }}""")
    wait(duration_ms / 1000 + 0.2)


def fade_from_black(page, duration_ms=800):
    """Fade from black to reveal the screen."""
    page.evaluate(f"""() => {{
        const el = document.getElementById('video-fade-overlay');
        el.style.transition = 'opacity {duration_ms}ms ease-in-out';
        el.style.opacity = '0';
    }}""")
    wait(duration_ms / 1000 + 0.2)


def show_title_card(page, section_label, title, subtitle="", hold_sec=2.0):
    """Show a full-screen title card with section label, title, and optional subtitle."""
    page.evaluate(f"""() => {{
        const card = document.getElementById('video-title-card');
        card.querySelector('.section-label').textContent = '{section_label}';
        card.querySelector('.section-title').textContent = '{title}';
        card.querySelector('.section-subtitle').textContent = '{subtitle}';
        card.style.opacity = '1';
    }}""")
    wait(0.8 + hold_sec)  # fade-in + hold
    page.evaluate("""() => {
        document.getElementById('video-title-card').style.opacity = '0';
    }""")
    wait(1.0)  # fade-out


def smooth_scroll_to(page, panel_selector, target_text, duration_ms=1000):
    """Smoothly scroll a panel until an element containing target_text is visible."""
    page.evaluate(f"""(text) => {{
        const panel = document.querySelector('{panel_selector}');
        if (!panel) return;
        const sections = panel.querySelectorAll('.section-title, .panel-section > div:first-child');
        for (const s of sections) {{
            if (s.textContent.includes(text)) {{
                s.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
                break;
            }}
        }}
    }}""", target_text)
    wait(duration_ms / 1000 + 0.3)


def smooth_scroll_panel(page, panel_selector, pixels, steps=10):
    """Smoothly scroll a panel by a given number of pixels."""
    step_size = pixels // steps
    for _ in range(steps):
        page.evaluate(f"""() => {{
            const panel = document.querySelector('{panel_selector}');
            if (panel) panel.scrollTop += {step_size};
        }}""")
        wait(0.05)
    wait(0.3)


def highlight_section(page, section_text, duration_ms=2000):
    """Add a brief cyan glow highlight to a panel section containing the given text."""
    page.evaluate(f"""(text) => {{
        const sections = document.querySelectorAll('.panel-section');
        for (const s of sections) {{
            const title = s.querySelector('.section-title');
            if (title && title.textContent.includes(text)) {{
                s.classList.add('highlight-pulse');
                setTimeout(() => s.classList.remove('highlight-pulse'), {duration_ms});
                break;
            }}
        }}
    }}""", section_text)
    wait(0.3)


def cinematic_fly(page, lat, lon, zoom, duration_sec=2.5):
    """Smoothly fly the Leaflet map to a location."""
    page.evaluate(f"""() => {{
        if (window.map) {{
            window.map.flyTo([{lat}, {lon}], {zoom}, {{
                duration: {duration_sec},
                easeLinearity: 0.25
            }});
        }}
    }}""")
    wait(duration_sec + 0.5)
```

- [ ] **Step 2: Verify the module imports cleanly**

```bash
python3 -c "from video_transitions import *; print('All helpers imported OK')"
```

- [ ] **Step 3: Commit**

```bash
git add video_transitions.py
git commit -m "feat: visual transition helpers for video recording (JS injection)"
```

---

### Task 4: Rewrite Recording Script with Choreographed Flow

**Files:**
- Modify: `record_combined.py`

**Ground Truth:** Playwright `page.video.save_as(path)` saves video cleanly. `page.evaluate()` for JS injection. `context.close()` triggers video write.

**Requires:** Task 1 (TTS narration), Task 2 (audio generation), Task 3 (transition helpers)
**Provides:** Rewritten `record_combined.py` with layer-synced choreography and smooth transitions

- [ ] **Step 1: Rewrite record_combined.py**

Replace the current recording flow with the choreographed version. Key structure:

```python
#!/usr/bin/env python3
"""Record the OSINT Atlas technical briefing with choreographed transitions.

Syncs UI navigation to the Brian voiceover narration. Each section shows
the matching intelligence layers with smooth visual transitions.

Usage:
  1. Start server: python3 test_atlas_server.py
  2. Record: python3 record_combined.py
  3. Output: videos/osint_atlas_briefing_final.mp4
"""
import os
import subprocess
import time
from playwright.sync_api import sync_playwright
from video_transitions import (
    wait, inject_transition_styles, fade_to_black, fade_from_black,
    show_title_card, smooth_scroll_to, smooth_scroll_panel,
    highlight_section, cinematic_fly,
)

BASE_URL = "http://127.0.0.1:8000"
VIDEO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "videos")

# ── Timing constants (calibrated to audio duration) ──
# These will be adjusted after measuring actual audio section lengths.
# Estimated from character ratios against ~652s total audio.
SEC1_DURATION = 310   # Section 1: Situation/Pipeline (~4:50-5:10)
SEC2_DURATION = 120   # Section 2: Key Findings (~2:00)
SEC3_DURATION = 120   # Section 3: Attack Path (~2:00)
SEC4_DURATION = 90    # Section 4: DMARC Finding (~1:30)
CLOSE_DURATION = 25   # Close (~0:25)
TITLE_CARD_TIME = 4.5 # Each title card: fade-in + hold + fade-out


def type_slowly(page, selector, text, delay=50):
    el = page.locator(selector)
    el.click()
    el.fill("")
    for char in text:
        el.type(char, delay=delay)


def open_console(page):
    try:
        page.locator("#atlasChatToggle").click(timeout=5000)
        wait(1)
    except Exception:
        pass


def send_chat(page, query, wait_seconds=30):
    try:
        input_el = page.locator("#atlasChatInput")
        input_el.click()
        input_el.fill("")
        for char in query:
            input_el.type(char, delay=35)
        wait(0.5)
        page.keyboard.press("Enter")
        wait(wait_seconds)
    except Exception as e:
        print(f"  Chat error: {e}")
        wait(wait_seconds)


def click_contractor(page, index):
    """Click a contractor marker by index to open its detail panel."""
    page.evaluate(f"""() => {{
        const markers = window.allMarkers || [];
        if (markers[{index}]) markers[{index}].fire('click');
    }}""")
    wait(2)


def main():
    os.makedirs(VIDEO_DIR, exist_ok=True)
    video_record_dir = os.path.join(VIDEO_DIR, "recording_tmp")
    os.makedirs(video_record_dir, exist_ok=True)

    with sync_playwright() as p:
        print("Launching browser...")
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=video_record_dir,
            record_video_size={"width": 1920, "height": 1080},
        )
        page = context.new_page()

        # ── LOAD APP ──
        page.goto(f"{BASE_URL}/atlas", wait_until="networkidle")
        wait(5)
        inject_transition_styles(page)
        wait(2)

        # Start with fade from black (cinematic opening)
        fade_to_black(page, duration_ms=100)  # instant black
        wait(1)
        fade_from_black(page, duration_ms=1500)  # slow reveal
        wait(8)  # Hold on map overview — opening narration

        # ════════════════════════════════════════════
        # SECTION 1: SITUATION / PIPELINE WALKTHROUGH
        # ════════════════════════════════════════════
        print("Section 1: Situation")
        fade_to_black(page)
        show_title_card(page, "◆ SECTION 1", "SITUATION", "DOE Contractor Attack Surface Assessment")
        fade_from_black(page)

        # Show map overview during "DOE maintains contractual relationships" narration
        wait(15)

        # Click Battelle (index 11) — richest data for pipeline demo
        click_contractor(page, 11)
        wait(3)

        # Slowly scroll through each layer as narration describes the pipeline
        # "domain discovery" → Mission Profile section visible at top
        wait(10)

        # "AI research layer validates each domain" → scroll to AI Research
        smooth_scroll_to(page, "#panelBody", "AI Research")
        highlight_section(page, "AI Research")
        wait(12)

        # "Domain verification follows" → already visible
        smooth_scroll_panel(page, "#panelBody", 200)
        wait(8)

        # "DNS intelligence extracts MX, SPF, DMARC" → scroll to Infrastructure
        smooth_scroll_to(page, "#panelBody", "Infrastructure")
        highlight_section(page, "Infrastructure")
        wait(10)

        # "Certificate transparency queries" → same section, scroll down
        smooth_scroll_panel(page, "#panelBody", 250)
        wait(10)

        # "Web fingerprinting" → scroll further
        smooth_scroll_panel(page, "#panelBody", 200)
        wait(8)

        # "Shodan queries identify internet-facing hosts" → scroll to Shodan
        smooth_scroll_to(page, "#panelBody", "Shodan")
        highlight_section(page, "Shodan")
        wait(12)

        # "Per-IP enrichment" → scroll to Host Intelligence
        smooth_scroll_to(page, "#panelBody", "Host Intelligence")
        highlight_section(page, "Host Intelligence")
        wait(10)

        # "ASN enumeration" → scroll down more
        smooth_scroll_panel(page, "#panelBody", 250)
        wait(8)

        # "On-premises classification" → scroll to On-Premises
        smooth_scroll_to(page, "#panelBody", "On-Prem")
        highlight_section(page, "On-Prem")
        wait(8)

        # "Service risk classification" → scroll to Dangerous Services
        smooth_scroll_to(page, "#panelBody", "Dangerous")
        highlight_section(page, "Dangerous")
        wait(10)

        # "NVD CVSS scoring" → scroll to vulnerabilities
        smooth_scroll_panel(page, "#panelBody", 300)
        wait(8)

        # "knowledge graph" → close panel, show map overview
        page.keyboard.press("Escape")
        wait(2)

        # Show heat map during knowledge graph description
        try:
            page.locator("#heatmapToggle").click(timeout=3000)
            wait(12)
            page.locator("#heatmapToggle").click(timeout=3000)
            wait(3)
        except Exception:
            wait(15)

        # Hold for "top-line numbers" transition
        wait(8)

        # ════════════════════════════════════════════
        # SECTION 2: KEY FINDINGS
        # ════════════════════════════════════════════
        print("Section 2: Key Findings")
        fade_to_black(page)
        show_title_card(page, "◆ SECTION 2", "KEY FINDINGS",
                       "Four Rivers Nuclear Partnership · $462M DOE Obligations")
        fade_from_black(page)

        # Open console and query
        open_console(page)
        wait(2)
        send_chat(page, "show me contractors with critical exposed services", wait_seconds=25)

        # "Four Rivers Nuclear Partnership" — click to open detail
        wait(5)

        # Scroll to show exposed services
        smooth_scroll_to(page, "#panelBody", "Shodan")
        highlight_section(page, "Shodan")
        wait(10)

        # Scroll to Host Intelligence for per-IP detail
        smooth_scroll_to(page, "#panelBody", "Host Intelligence")
        highlight_section(page, "Host Intelligence")
        wait(15)

        # Scroll to Dangerous Services
        smooth_scroll_to(page, "#panelBody", "Dangerous")
        highlight_section(page, "Dangerous")
        wait(15)

        # Show hosting attribution
        smooth_scroll_panel(page, "#panelBody", 200)
        wait(10)

        # ════════════════════════════════════════════
        # SECTION 3: ATTACK PATH ANALYSIS
        # ════════════════════════════════════════════
        print("Section 3: Attack Path Analysis")
        fade_to_black(page)
        show_title_card(page, "◆ SECTION 3", "ATTACK PATH ANALYSIS",
                       "MITRE ATT&CK Mapped Kill Chains")
        fade_from_black(page)

        # Generate kill chain for current contractor
        send_chat(page, "generate a kill chain for this contractor", wait_seconds=40)

        # Hold on kill chain result
        smooth_scroll_panel(page, "#panelBody", 300, steps=15)
        wait(15)

        # Second example — UC Regents
        send_chat(page, "show me the highest risk Research & Labs contractor", wait_seconds=30)
        wait(5)

        # Scroll through their data
        smooth_scroll_to(page, "#panelBody", "Host Intelligence")
        highlight_section(page, "Host Intelligence")
        wait(15)

        smooth_scroll_panel(page, "#panelBody", 300, steps=15)
        wait(10)

        # ════════════════════════════════════════════
        # SECTION 4: FINDING OF NOTE — DMARC
        # ════════════════════════════════════════════
        print("Section 4: Finding of Note")
        fade_to_black(page)
        show_title_card(page, "◆ FINDING OF NOTE",
                       "EMAIL AUTHENTICATION",
                       "Management Company DMARC Gap")
        fade_from_black(page)

        # Query about DMARC
        send_chat(page, "show me nuclear lab management companies with no DMARC", wait_seconds=30)

        # Scroll to DNS section to show DMARC=none
        smooth_scroll_to(page, "#panelBody", "Infrastructure")
        highlight_section(page, "Infrastructure")
        wait(20)

        # Scroll to show DMARC policy specifically
        smooth_scroll_panel(page, "#panelBody", 150)
        wait(15)

        # ════════════════════════════════════════════
        # CLOSE
        # ════════════════════════════════════════════
        print("Close")
        # Close panel, show heat map for closing shot
        page.keyboard.press("Escape")
        wait(2)
        try:
            page.locator("#heatmapToggle").click(timeout=3000)
            wait(3)
        except Exception:
            pass

        # Cinematic zoom out
        cinematic_fly(page, 39.5, -98.0, 4, duration_sec=3.0)
        wait(10)

        # Final fade to black
        fade_to_black(page, duration_ms=2000)
        wait(3)

        print("Recording complete.")

        # Save video
        dst = os.path.join(VIDEO_DIR, "osint_atlas_briefing.webm")
        page.video.save_as(dst)
        context.close()
        browser.close()
        size = os.path.getsize(dst)
        print(f"Saved: {dst} ({size / 1024 / 1024:.1f} MB)")

    # ── Merge with audio ──
    print("\nMerging video + audio...")
    video_file = os.path.join(VIDEO_DIR, "osint_atlas_briefing.webm")
    audio_file = os.path.join(VIDEO_DIR, "audio", "osint_atlas_briefing.mp3")
    output_file = os.path.join(VIDEO_DIR, "osint_atlas_briefing_final.mp4")

    if os.path.exists(video_file) and os.path.exists(audio_file):
        result = subprocess.run([
            "ffmpeg", "-y",
            "-i", video_file,
            "-i", audio_file,
            "-c:v", "libx264",
            "-c:a", "aac",
            "-shortest",
            "-movflags", "+faststart",
            output_file,
        ], capture_output=True, text=True)

        if result.returncode == 0:
            size = os.path.getsize(output_file)
            print(f"Final video: {output_file} ({size / 1024 / 1024:.1f} MB)")
        else:
            print(f"ffmpeg error: {result.stderr[:300]}")
    else:
        print("Missing video or audio file — skipping merge")


if __name__ == "__main__":
    main()
```

The timing constants (SEC1_DURATION, etc.) are estimates. After generating audio, we measure actual section durations and calibrate the wait() calls.

- [ ] **Step 2: Verify the script parses cleanly**

```bash
python3 -c "import ast; ast.parse(open('record_combined.py').read()); print('Syntax OK')"
```

- [ ] **Step 3: Commit**

```bash
git add record_combined.py
git commit -m "feat: choreographed recording with smooth transitions synced to narration"
```

---

### Task 5: Generate Audio, Record, and Merge

**Files:**
- Output: `videos/audio/osint_atlas_briefing.mp3`
- Output: `videos/osint_atlas_briefing.webm`
- Output: `videos/osint_atlas_briefing_final.mp4`

**Requires:** Tasks 1-4

- [ ] **Step 1: Generate new audio**

```bash
python3 generate_voiceover.py --video combined --audio-only
```

Verify:
```bash
ffprobe -v quiet -show_entries format=duration -of csv=p=0 videos/audio/osint_atlas_briefing.mp3
```

- [ ] **Step 2: Start the server (in background)**

```bash
python3 test_atlas_server.py &
# Wait for "Uvicorn running on http://127.0.0.1:8000"
```

- [ ] **Step 3: Run the recording**

```bash
python3 record_combined.py
```

Expected output:
- `videos/osint_atlas_briefing.webm` (raw recording, ~50-60MB)
- `videos/osint_atlas_briefing_final.mp4` (merged with audio)

- [ ] **Step 4: Verify output**

```bash
ffprobe -v quiet -show_entries format=duration -of csv=p=0 videos/osint_atlas_briefing_final.mp4
ls -lh videos/osint_atlas_briefing_final.mp4
```

Duration should be ~10-11 minutes. File should be ~50-60MB.

---

### Integration Test Spec

The integration test is the final video itself:
1. Audio generates without error (single API call, no chunking artifacts)
2. Recording completes without Playwright crashes
3. ffmpeg merges successfully
4. Final MP4 has both video and audio streams
5. Duration matches the narration length (~10-11 min)

Verification:
```bash
ffprobe -v quiet -show_entries stream=codec_type -of csv=p=0 videos/osint_atlas_briefing_final.mp4
# Expected: two lines — "video" and "audio"
```
