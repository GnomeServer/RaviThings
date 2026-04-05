#!/usr/bin/env python3
"""
Record the OSINT Atlas technical briefing with choreographed transitions.

Rewritten narration: demo-first order (show capabilities, then explain pipeline).
Brian voiceover synced to UI demonstrations with smooth visual transitions.

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
    show_image_overlay, hide_image_overlay,
)

BASE_URL = "http://127.0.0.1:8000"
VIDEO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "videos")
PANELS_DIR = os.path.join(VIDEO_DIR, "panels")

# Panel images for pipeline visualization (Act 6)
PANEL_IMAGES = {
    "discovery":      os.path.join(PANELS_DIR, "panel1_discovery.jpg"),
    "infrastructure": os.path.join(PANELS_DIR, "panel2_infrastructure.jpg"),
    "classification": os.path.join(PANELS_DIR, "panel3_classification.jpg"),
    "synthesis":      os.path.join(PANELS_DIR, "panel4_synthesis.jpg"),
}

# Contractor indices (from contractors.json)
BATTELLE_IDX = 11  # Battelle Memorial Institute — richest data (11/14 layers)


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
    """Click a contractor marker by array index."""
    page.evaluate("""(idx) => {
        const markers = window.allMarkers || [];
        if (markers[idx]) markers[idx].fire('click');
    }""", index)
    wait(2.5)


def scroll_panel_to_top(page):
    """Reset the detail panel scroll position."""
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

        # ═════��════════════════════════════════════════════════
        # ACT 1: THE HOOK (~45s)
        # "What you're looking at is every DOE contractor..."
        # "The platform takes plain English queries..."
        # Visual: Map overview, then console query
        # ═══���══════════════════════════════════════════════════
        print("Act 1: The Hook")

        # "What you're looking at..." — hold on full map with threat dashboard
        wait(20)

        # "The platform takes plain English queries. Watch..."
        open_console(page)
        wait(3)

        # "Show me contractors with critical exposed services."
        send_chat(page, "show me contractors with critical exposed services",
                  wait_seconds=20)
        wait(5)

        # ════════════════════════════════════════��═════════════
        # ACT 2: THE FINDINGS (~2.5 min)
        # "This is Four Rivers Nuclear Partnership..."
        # Visual: Four Rivers detail panel, services, hosting
        # ══════════════════════════════���═══════════════════════
        print("Act 2: The Findings")
        fade_to_black(page)
        show_title_card(page,
                        "\u25c6  CASE STUDY",
                        "FOUR RIVERS NUCLEAR",
                        "$462M DOE Obligations \u00b7 Paducah Gaseous Diffusion Plant",
                        hold_sec=2.5)
        fade_from_black(page)

        # "This is Four Rivers Nuclear Partnership..."
        wait(10)

        # "On a single IP address..." → scroll to Shodan/Host Intelligence
        smooth_scroll_to(page, "#panelBody", "Shodan")
        highlight_section(page, "Shodan")
        wait(15)

        smooth_scroll_to(page, "#panelBody", "Host Intelligence")
        highlight_section(page, "Host Intelligence")
        wait(20)

        # "Three database engines..." → Dangerous Services
        smooth_scroll_to(page, "#panelBody", "Dangerous")
        highlight_section(page, "Dangerous")
        wait(15)

        # "Hosted on GoDaddy shared infrastructure" → scroll to hosting badges
        smooth_scroll_panel(page, "#panelBody", 200)
        wait(10)

        # ═══════════════════════════════════���══════════════════
        # ACT 3: ATTACK PATH (~2.5 min)
        # "...the system generates an attack path mapped to MITRE ATT&CK"
        # "A second example. The University of California system."
        # Visual: Kill chain, then UC Regents
        # ══��═══════════════════════���═══════════════════════════
        print("Act 3: Attack Path")
        fade_to_black(page)
        show_title_card(page,
                        "\u25c6  ATTACK PATH",
                        "MITRE ATT&CK KILL CHAIN",
                        "Automated from Observed Services",
                        hold_sec=2.5)
        fade_from_black(page)

        # "...the system generates an attack path"
        send_chat(page, "generate a kill chain for this contractor",
                  wait_seconds=40)

        # Show kill chain result
        smooth_scroll_panel(page, "#panelBody", 400, steps=20)
        wait(20)

        # "A second example. The University of California system."
        send_chat(page, "show me the highest risk Research & Labs contractor",
                  wait_seconds=30)
        wait(5)

        smooth_scroll_to(page, "#panelBody", "Host Intelligence")
        highlight_section(page, "Host Intelligence")
        wait(20)

        # "OpenSSH six-point-zero-p-one... CVE..."
        smooth_scroll_panel(page, "#panelBody", 350, steps=15)
        wait(15)

        # ══════��═══════════════════════��═══════════════════════
        # ACT 4: THE BLIND SPOT — DMARC (~2 min)
        # "A finding that may be the most operationally significant..."
        # Visual: DMARC query, DNS section
        # ══════════════════════════════════════════════════════
        print("Act 4: The Blind Spot — DMARC")
        fade_to_black(page)
        show_title_card(page,
                        "\u25c6  FINDING OF NOTE",
                        "EMAIL AUTHENTICATION",
                        "Management Company DMARC Gap",
                        hold_sec=2.5)
        fade_from_black(page)

        send_chat(page, "show me nuclear lab management companies with no DMARC",
                  wait_seconds=30)

        smooth_scroll_to(page, "#panelBody", "Infrastructure")
        highlight_section(page, "Infrastructure")
        wait(20)

        smooth_scroll_panel(page, "#panelBody", 150)
        wait(20)

        # ═════════��═════════════════════════��══════════════════
        # ACT 5: THE FULL PICTURE + IMPLICATIONS (~2.5 min)
        # "Let me put the full picture in front of you..."
        # "What that means in practice..."
        # Visual: Threat dashboard stats, heat map
        # ═══════════════════════���══════════════════════════════
        print("Act 5: The Full Picture")
        fade_to_black(page)
        show_title_card(page,
                        "\u25c6  ASSESSMENT",
                        "ATTACK SURFACE",
                        "The Full Picture",
                        hold_sec=2.5)
        fade_from_black(page)

        # Close panel, show full map with threat dashboard
        page.keyboard.press("Escape")
        wait(3)

        # "Of 2,214 DOE contractors..." — hold on threat dashboard numbers
        wait(30)

        # "This is not a projection..." → show heat map
        try:
            page.locator("#heatmapToggle").click(timeout=3000)
            wait(3)
        except Exception:
            pass

        # "What that means in practice..." — hold on heat map during implications
        wait(50)

        # "The supply chain is the perimeter..." — continue on heat map
        wait(40)

        # Turn off heat map before pipeline section
        try:
            page.locator("#heatmapToggle").click(timeout=3000)
            wait(2)
        except Exception:
            pass

        # ════════════════════════════════════���═════════════════
        # ACT 6: HOW WE BUILT IT — 14-LAYER PIPELINE (~2.5 min)
        # "So — how did we get all of this?"
        # Visual: 4 quad-panel images
        # ═��══════════════════════���════════════════════════════���
        print("Act 6: The Pipeline")
        fade_to_black(page)
        show_title_card(page,
                        "\u25c6  METHODOLOGY",
                        "14-LAYER PIPELINE",
                        "Automated Open-Source Collection Architecture",
                        hold_sec=2.5)
        fade_from_black(page)

        panels_available = all(os.path.exists(p) for p in PANEL_IMAGES.values())

        if panels_available:
            # Panel 1: Discovery & Validation (layers 1-4)
            show_image_overlay(page, PANEL_IMAGES["discovery"], fade_in_ms=1000)
            wait(40)
            hide_image_overlay(page, fade_out_ms=600)
            wait(0.5)

            # Panel 2: Infrastructure Mapping (layers 5-8)
            show_image_overlay(page, PANEL_IMAGES["infrastructure"], fade_in_ms=1000)
            wait(35)
            hide_image_overlay(page, fade_out_ms=600)
            wait(0.5)

            # Panel 3: Network Classification (layers 9-12)
            show_image_overlay(page, PANEL_IMAGES["classification"], fade_in_ms=1000)
            wait(30)
            hide_image_overlay(page, fade_out_ms=600)
            wait(0.5)

            # Panel 4: Intelligence Synthesis (layers 13-14 + summary)
            show_image_overlay(page, PANEL_IMAGES["synthesis"], fade_in_ms=1000)
            wait(25)
            hide_image_overlay(page, fade_out_ms=600)
        else:
            print("  Panel images not found — using detail-panel fallback")
            click_contractor_by_index(page, BATTELLE_IDX)
            scroll_panel_to_top(page)
            wait(3)
            # Abbreviated scrollthrough
            wait(15)
            smooth_scroll_to(page, "#panelBody", "AI Research")
            highlight_section(page, "AI Research")
            wait(15)
            smooth_scroll_to(page, "#panelBody", "Infrastructure")
            highlight_section(page, "Infrastructure")
            wait(20)
            smooth_scroll_to(page, "#panelBody", "Shodan")
            highlight_section(page, "Shodan")
            wait(20)
            smooth_scroll_to(page, "#panelBody", "Dangerous")
            highlight_section(page, "Dangerous")
            wait(15)
            smooth_scroll_panel(page, "#panelBody", 300)
            wait(15)
            page.keyboard.press("Escape")
            wait(2)

        # ═════════════���═════════════════════════════════��══════
        # ACT 7: CONCLUSION (~2 min)
        # "The data shows something no single line item reveals..."
        # "Four things make this genuinely alarming..."
        # Visual: Heat map, cinematic zoom out, fade to black
        # ═════════════════��═════════════════════════════���══════
        print("Act 7: Conclusion")
        fade_to_black(page, duration_ms=600)
        show_title_card(page,
                        "\u25c6  ASSESSMENT",
                        "CONCLUSIONS",
                        "",
                        hold_sec=2.0)
        fade_from_black(page)

        # "The data shows something no single line item reveals..."
        # Show heat map for the aggregate-risk visual
        try:
            page.locator("#heatmapToggle").click(timeout=3000)
            wait(3)
        except Exception:
            pass

        # Hold during the four alarming points
        wait(80)

        # "This assessment was conducted entirely from open sources..."
        # Cinematic zoom out
        cinematic_fly(page, 39.5, -98.0, 4, duration_sec=3.0)
        wait(15)

        # "Classification: unclassified" — final fade to black
        fade_to_black(page, duration_ms=2000)
        wait(5)

        print("Recording complete.")

        # ── Save video ──
        dst = os.path.join(VIDEO_DIR, "osint_atlas_briefing.webm")
        page.close()
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
