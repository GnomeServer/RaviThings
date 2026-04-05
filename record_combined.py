#!/usr/bin/env python3
"""
Record the OSINT Atlas technical briefing with choreographed transitions.

Syncs UI navigation to the Brian voiceover narration. Each section shows
the matching intelligence layers with smooth visual transitions.

Usage:
  1. Start server: python3 test_atlas_server.py
  2. Record: python3 record_combined.py
  3. Output: videos/osint_atlas_briefing_final.mp4
"""

import os
import subprocess
from playwright.sync_api import sync_playwright
from video_transitions import (
    wait, inject_transition_styles, fade_to_black, fade_from_black,
    show_title_card, smooth_scroll_to, smooth_scroll_panel,
    highlight_section, cinematic_fly, type_slowly,
)

BASE_URL = "http://127.0.0.1:8000"
VIDEO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "videos")

# Contractor indices (from contractors.json)
BATTELLE_IDX = 11      # Battelle Memorial Institute — richest data (11/14 layers)
FOUR_RIVERS_IDX = None  # Will be found by name search


def open_console(page):
    """Open the command console panel."""
    try:
        page.locator("#atlasChatToggle").click(timeout=5000)
        wait(1)
    except Exception:
        pass


def send_chat(page, query, wait_seconds=30):
    """Type a query into the console and send it."""
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


def click_contractor_by_index(page, index):
    """Click a contractor marker by array index to open its detail panel."""
    page.evaluate("""(idx) => {
        const markers = window.allMarkers || [];
        if (markers[idx]) markers[idx].fire('click');
    }""", index)
    wait(2.5)


def scroll_panel_to_top(page):
    """Reset the detail panel scroll to the top."""
    page.evaluate("""() => {
        const panel = document.querySelector('#panelBody');
        if (panel) panel.scrollTop = 0;
    }""")
    wait(0.3)


def main():
    os.makedirs(VIDEO_DIR, exist_ok=True)
    record_dir = os.path.join(VIDEO_DIR, "recording_tmp")
    os.makedirs(record_dir, exist_ok=True)

    with sync_playwright() as p:
        print("Launching browser...")
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=record_dir,
            record_video_size={"width": 1920, "height": 1080},
        )
        page = context.new_page()

        # ── LOAD APP ──────────────────────────────────────────
        page.goto(f"{BASE_URL}/atlas", wait_until="networkidle")
        wait(3)
        inject_transition_styles(page)

        # Cinematic opening: start black, slow reveal
        fade_to_black(page, duration_ms=50)
        wait(0.5)
        fade_from_black(page, duration_ms=1500)
        wait(6)  # Hold on map overview — classification header narration

        # ══════════════════════════════════════════════════════
        # SECTION 1: SITUATION / PIPELINE WALKTHROUGH
        # Narration: ~5 min covering 14 pipeline layers
        # Visual: Click Battelle, scroll through each panel section
        # ══════════════════════════════════════════════════════
        print("Section 1: Situation")
        fade_to_black(page)
        show_title_card(page,
                        "\u25c6  SECTION 1",
                        "SITUATION",
                        "DOE Contractor Attack Surface Assessment",
                        hold_sec=2.5)
        fade_from_black(page)

        # "DOE maintains contractual relationships..." — show the full map
        wait(12)

        # "We conducted an open-source intelligence assessment..." — still map overview
        wait(10)

        # "The collection architecture is a fourteen-layer pipeline..."
        # Click Battelle to open detail panel — walk through layers
        click_contractor_by_index(page, BATTELLE_IDX)
        scroll_panel_to_top(page)
        wait(3)

        # "domain discovery" — Mission Profile visible at top of panel
        wait(10)

        # "AI research layer validates each domain" → scroll to AI Research
        smooth_scroll_to(page, "#panelBody", "AI Research")
        highlight_section(page, "AI Research")
        wait(14)

        # "Domain verification follows" → scroll slightly
        smooth_scroll_panel(page, "#panelBody", 200)
        wait(10)

        # "DNS intelligence extracts MX, SPF, DMARC" → Infrastructure section
        smooth_scroll_to(page, "#panelBody", "Infrastructure")
        highlight_section(page, "Infrastructure")
        wait(12)

        # "Certificate transparency queries crt.sh" → scroll down in same section
        smooth_scroll_panel(page, "#panelBody", 250)
        wait(12)

        # "Web fingerprinting analyzes HTTP response headers" → scroll to web data
        smooth_scroll_panel(page, "#panelBody", 200)
        wait(10)

        # "Shodan queries identify internet-facing hosts" → Shodan section
        smooth_scroll_to(page, "#panelBody", "Shodan")
        highlight_section(page, "Shodan")
        wait(12)

        # "Per-IP enrichment returns service banners" → Host Intelligence
        smooth_scroll_to(page, "#panelBody", "Host Intelligence")
        highlight_section(page, "Host Intelligence")
        wait(12)

        # "ASN enumeration... On-premises classification" → On-Prem section
        smooth_scroll_to(page, "#panelBody", "On-Prem")
        highlight_section(page, "On-Prem")
        wait(10)

        # "Service risk classification" → Dangerous Services
        smooth_scroll_to(page, "#panelBody", "Dangerous")
        highlight_section(page, "Dangerous")
        wait(10)

        # "NVD CVSS scoring" → scroll to vulnerabilities
        smooth_scroll_panel(page, "#panelBody", 300)
        wait(10)

        # "knowledge graph... 24,700 nodes..." → close panel, show network graph briefly
        page.keyboard.press("Escape")
        wait(2)

        # Toggle heat map for the knowledge graph / geographic concentration visual
        try:
            page.locator("#heatmapToggle").click(timeout=3000)
            wait(12)
            page.locator("#heatmapToggle").click(timeout=3000)
            wait(3)
        except Exception:
            wait(15)

        # Pause before Section 2 transition
        wait(5)

        # ══════════════════════════════════════════════════════
        # SECTION 2: KEY FINDINGS
        # Narration: ~2 min — top-line numbers, Four Rivers case
        # Visual: Console query, Four Rivers detail panel
        # ══════════════════════════════════════════════════════
        print("Section 2: Key Findings")
        fade_to_black(page)
        show_title_card(page,
                        "\u25c6  SECTION 2",
                        "KEY FINDINGS",
                        "Four Rivers Nuclear Partnership \u00b7 $462M DOE Obligations",
                        hold_sec=2.5)
        fade_from_black(page)

        # "Top-line numbers..." — show map with threat dashboard visible
        wait(15)

        # "The platform provides a natural language interface..."
        open_console(page)
        wait(2)

        # "I'll demonstrate with a specific case" → query
        send_chat(page, "show me contractors with critical exposed services",
                  wait_seconds=25)
        wait(5)

        # "Four Rivers Nuclear Partnership..." — show detail panel
        # Scroll to Shodan section
        smooth_scroll_to(page, "#panelBody", "Shodan")
        highlight_section(page, "Shodan")
        wait(12)

        # "On a single IP address..." → Host Intelligence
        smooth_scroll_to(page, "#panelBody", "Host Intelligence")
        highlight_section(page, "Host Intelligence")
        wait(15)

        # "Nine services. Three database engines." → Dangerous Services
        smooth_scroll_to(page, "#panelBody", "Dangerous")
        highlight_section(page, "Dangerous")
        wait(15)

        # "Hosted on GoDaddy shared infrastructure" → scroll to hosting badges
        smooth_scroll_panel(page, "#panelBody", 200)
        wait(8)

        # ══════════════════════════════════════════════════════
        # SECTION 3: ATTACK PATH ANALYSIS
        # Narration: ~2 min — kill chain, UC Regents
        # Visual: Kill chain generation, UC Regents detail
        # ══════════════════════════════════════════════════════
        print("Section 3: Attack Path Analysis")
        fade_to_black(page)
        show_title_card(page,
                        "\u25c6  SECTION 3",
                        "ATTACK PATH ANALYSIS",
                        "MITRE ATT&CK Mapped Kill Chains",
                        hold_sec=2.5)
        fade_from_black(page)

        # "the system generates MITRE ATT&CK mapped attack paths" → kill chain
        send_chat(page, "generate a kill chain for this contractor",
                  wait_seconds=40)

        # Show kill chain result — scroll through it
        smooth_scroll_panel(page, "#panelBody", 400, steps=20)
        wait(15)

        # "A second example. The University of California system"
        send_chat(page, "show me the highest risk Research & Labs contractor",
                  wait_seconds=30)
        wait(5)

        # Scroll to their Host Intelligence
        smooth_scroll_to(page, "#panelBody", "Host Intelligence")
        highlight_section(page, "Host Intelligence")
        wait(15)

        # "OpenSSH six-point-zero-p-one... CVE..." → scroll to CVEs
        smooth_scroll_panel(page, "#panelBody", 350, steps=15)
        wait(12)

        # ══════════════════════════════════════════════════════
        # SECTION 4: FINDING OF NOTE — DMARC
        # Narration: ~2 min — management company email gap
        # Visual: DMARC query, DNS section
        # ══════════════════════════════════════════════════════
        print("Section 4: Finding of Note — DMARC")
        fade_to_black(page)
        show_title_card(page,
                        "\u25c6  FINDING OF NOTE",
                        "EMAIL AUTHENTICATION",
                        "Management Company DMARC Gap",
                        hold_sec=2.5)
        fade_from_black(page)

        # "The national laboratory .gov domains have DMARC set to reject"
        send_chat(page, "show me nuclear lab management companies with no DMARC",
                  wait_seconds=30)
        wait(5)

        # Scroll to Infrastructure/DNS section to show DMARC policy
        smooth_scroll_to(page, "#panelBody", "Infrastructure")
        highlight_section(page, "Infrastructure")
        wait(15)

        # "DMARC record: none" — scroll to highlight the DMARC field
        smooth_scroll_panel(page, "#panelBody", 150)
        wait(20)

        # "The laboratory .gov domains are hardened. The management company domains... are not."
        wait(10)

        # ══════════════════════════════════════════════════════
        # CLOSE
        # Narration: ~25s — "conducted entirely from open sources"
        # Visual: Heat map, cinematic zoom out, fade to black
        # ══════════════════════════════════════════════════════
        print("Close")
        fade_to_black(page, duration_ms=600)
        fade_from_black(page, duration_ms=600)

        # Close panel, show full map
        page.keyboard.press("Escape")
        wait(2)

        # Heat map for closing visual
        try:
            page.locator("#heatmapToggle").click(timeout=3000)
            wait(3)
        except Exception:
            pass

        # Cinematic zoom out to full US view
        cinematic_fly(page, 39.5, -98.0, 4, duration_sec=3.0)
        wait(12)

        # "Classification: UNCLASSIFIED" — final fade to black
        fade_to_black(page, duration_ms=2000)
        wait(4)

        print("Recording complete.")

        # ── Save video ──
        dst = os.path.join(VIDEO_DIR, "osint_atlas_briefing.webm")
        page.close()  # Must close page before save_as
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
