#!/usr/bin/env python3
"""
Record the OSINT Atlas technical briefing — audio-aligned choreography.

Every visual action is timed to a specific narration timestamp calculated
from character positions in the script. No reliance on LLM chat responses
for contractor selection — all navigation is direct via openDetailPanel().

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
    highlight_section, cinematic_fly, type_slowly,
    show_image_overlay, hide_image_overlay,
    open_contractor, zoom_section, unzoom_section, ensure_dark_background,
)

BASE_URL = "http://127.0.0.1:8000"
VIDEO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "videos")
PANELS_DIR = os.path.join(VIDEO_DIR, "panels")

PANEL_IMAGES = {
    "discovery":      os.path.join(PANELS_DIR, "panel1_discovery.jpg"),
    "infrastructure": os.path.join(PANELS_DIR, "panel2_infrastructure.jpg"),
    "classification": os.path.join(PANELS_DIR, "panel3_classification.jpg"),
    "synthesis":      os.path.join(PANELS_DIR, "panel4_synthesis.jpg"),
}

# ── Contractor indices (verified from contractors.json) ──
FOUR_RIVERS_IDX = 199   # Four Rivers Nuclear Partnership — $462M
UC_REGENTS_IDX = 7       # Regents of the University of California — $3.06B
TRIAD_IDX = 10           # Triad National Security (Los Alamos) — $14.9B
BATTELLE_IDX = 11        # Battelle Memorial Institute — $3.93B

# ── Audio timestamps (calculated from char positions, ~810s total) ──
# These are approximate — the recording should be ~5-10s ahead of each
# timestamp to give the visual time to settle before the narration hits.
T = {
    "platform_takes":       35,   # "The platform takes plain English"
    "show_me":              42,   # "Show me contractors with critical"
    "four_rivers":          57,   # "This is Four Rivers Nuclear"
    "on_single_ip":         70,   # "On a single IP address"
    "three_databases":     102,   # "Three database engines"
    "attack_path":         120,   # "the system generates an attack path"
    "uc_regents":          163,   # "A second example. The University of California"
    "fourteen_year_ssh":   203,   # "A fourteen-year-old SSH"
    "dmarc_finding":       210,   # "A finding that may be"
    "triad_manages":       239,   # "Triad National Security manages"
    "lab_hardened":        290,   # "The laboratory dot gov domains are hardened"
    "full_picture":        300,   # "Let me put the full picture"
    "not_projection":      389,   # "This is not a projection"
    "what_means":          409,   # "What that means in practice"
    "supply_chain":        489,   # "The supply chain is the perimeter"
    "how_we_built":        500,   # "So — how did we get all of this"
    "domain_discovery":    511,   # "It starts with domain discovery"
    "ct_queries":          556,   # "Certificate transparency queries"
    "asn_enum":            596,   # "ASN enumeration"
    "nvd_scoring":         621,   # "NVD scoring"
    "produced_everything": 646,   # "That is what produced everything"
    "data_shows":          650,   # "The data shows something"
    "four_things":         691,   # "Four things make this genuinely"
    "first_supply":        697,   # "First — the supply chain"
    "second_dmarc":        720,   # "Second — the DMARC gap"
    "third_observable":    747,   # "Third — the exposure"
    "fourth_scale":        766,   # "Fourth — scale defeats"
    "assessment_conducted":788,   # "This assessment was conducted"
    "classification":      801,   # "Classification: unclassified"
}


def elapsed(start_time):
    """Return seconds elapsed since recording started."""
    return time.time() - start_time


def wait_until(start_time, target_sec):
    """Wait until the recording clock reaches target_sec.

    If we're already past the target, return immediately.
    This keeps the recording synchronized to audio timestamps.
    """
    remaining = target_sec - elapsed(start_time)
    if remaining > 0:
        time.sleep(remaining)


SCREENSHOT_DIR = os.path.join(VIDEO_DIR, "alignment_check")


def snap(page, t0, label):
    """Take a screenshot for alignment verification."""
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    sec = int(time.time() - t0)
    path = os.path.join(SCREENSHOT_DIR, f"{sec:04d}s_{label}.png")
    try:
        page.screenshot(path=path)
        print(f"  SNAP [{sec//60}:{sec%60:02d}] {label}")
    except Exception:
        pass


def open_console(page):
    try:
        page.locator("#atlasChatToggle").click(timeout=5000)
        wait(1)
    except Exception:
        pass


def send_chat(page, query, wait_seconds=25):
    try:
        input_el = page.locator("#atlasChatInput")
        input_el.click()
        input_el.fill("")
        for char in query:
            input_el.type(char, delay=30)
        wait(0.3)
        page.keyboard.press("Enter")
        wait(wait_seconds)
    except Exception as e:
        print(f"  Chat error: {e}")
        wait(wait_seconds)


def scroll_panel_to_top(page):
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

        # ── Prevent white flash ──
        ensure_dark_background(page)
        page.goto(f"{BASE_URL}/atlas", wait_until="networkidle")
        wait(2)
        inject_transition_styles(page)

        # ── INTRO: Dark fade-in ──
        fade_to_black(page, duration_ms=50)  # Start fully black
        wait(1)

        # Show a title card before revealing the map
        show_title_card(page,
                        "OSINT ATLAS",
                        "DOE CONTRACTOR ATTACK SURFACE",
                        "UNCLASSIFIED // FOR OFFICIAL USE ONLY",
                        hold_sec=3.0)

        # Reveal the map
        fade_from_black(page, duration_ms=1500)

        # ── START CLOCK ──
        # The audio starts here. All subsequent actions are timed
        # relative to this moment.
        t0 = time.time()
        print("Audio clock started.")

        # ═══════════════════════════════════════════════════════
        # ACT 1: THE HOOK (0:00 – 0:57)
        # "What you're looking at..." → console query → map flies
        # ═══════════════════════════════════════════════════════
        print("Act 1: The Hook")

        # 0:00–0:35 — "What you're looking at is every DOE contractor..."
        # Hold on map overview with threat dashboard visible
        snap(page, t0, "01_map_overview")
        wait_until(t0, T["platform_takes"] - 5)

        # 0:35 — "The platform takes plain English queries. Watch..."
        open_console(page)
        wait(2)

        # 0:42 — "Show me contractors with critical exposed services."
        # Type the query visually, then send
        type_slowly(page, "#atlasChatInput",
                    "show me contractors with critical exposed services", delay_ms=30)
        wait(0.5)
        page.keyboard.press("Enter")

        # Wait for LLM response + map animation (fly_to happens automatically)
        wait(12)

        # ═══════════════════════════════════════════════════════
        # ACT 2: FOUR RIVERS (0:57 – 2:00)
        # Direct navigation — don't rely on chat results
        # ═══════════════════════════════════════════════════════
        print("Act 2: Four Rivers")

        # 0:57 — "This is Four Rivers Nuclear Partnership."
        # Fly to Four Rivers and open its detail panel
        wait_until(t0, T["four_rivers"] - 3)
        snap(page, t0, "02_before_four_rivers")
        open_contractor(page, FOUR_RIVERS_IDX, fly=True, fly_zoom=10, fly_duration=2.0)
        scroll_panel_to_top(page)

        # 1:10 — "On a single IP address, Shodan product banners..."
        wait_until(t0, T["on_single_ip"] - 2)
        snap(page, t0, "03_four_rivers_panel_open")
        smooth_scroll_to(page, "#panelBody", "Shodan")
        highlight_section(page, "Shodan")
        wait(3)

        # Scroll to Host Intelligence for service details
        smooth_scroll_to(page, "#panelBody", "Host Intelligence")
        highlight_section(page, "Host Intelligence")
        zoom_section(page, "Host Intelligence", scale=1.15)

        # 1:42 — "Three database engines. Remote desktop. SMB version one."
        wait_until(t0, T["three_databases"] - 2)
        unzoom_section(page, "Host Intelligence")
        smooth_scroll_to(page, "#panelBody", "Dangerous")
        highlight_section(page, "Dangerous")
        zoom_section(page, "Dangerous", scale=1.15)
        wait(8)
        unzoom_section(page, "Dangerous")

        # "Hosted on GoDaddy shared infrastructure" — scroll to hosting badges
        smooth_scroll_panel(page, "#panelBody", 200)
        wait(5)

        # ═══════════════════════════════════════════════════════
        # ACT 3: ATTACK PATH (2:00 – 3:30)
        # Kill chain for Four Rivers, then UC Regents
        # ═══════════════════════════════════════════════════════
        print("Act 3: Attack Path")

        # 2:00 — "the system generates an attack path mapped to MITRE ATT&CK"
        wait_until(t0, T["attack_path"] - 3)
        fade_to_black(page)
        show_title_card(page, "\u25c6  ATTACK PATH",
                        "MITRE ATT&CK KILL CHAIN",
                        "Automated from Observed Services", hold_sec=2.0)
        fade_from_black(page)

        # Generate kill chain via console (this one IS the right contractor)
        send_chat(page, "generate a kill chain for Four Rivers Nuclear",
                  wait_seconds=35)

        # Scroll through kill chain result
        smooth_scroll_panel(page, "#panelBody", 400, steps=20)

        # 2:43 — "A second example. The University of California system."
        wait_until(t0, T["uc_regents"] - 3)
        snap(page, t0, "05_before_uc_regents")

        # DIRECT navigation to UC Regents — don't use a query
        open_contractor(page, UC_REGENTS_IDX, fly=True, fly_zoom=10, fly_duration=2.0)
        scroll_panel_to_top(page)
        wait(2)

        # Scroll to their Host Intelligence
        smooth_scroll_to(page, "#panelBody", "Host Intelligence")
        highlight_section(page, "Host Intelligence")
        zoom_section(page, "Host Intelligence", scale=1.15)

        # 3:23 — "A fourteen-year-old SSH implementation..."
        wait_until(t0, T["fourteen_year_ssh"] - 2)
        unzoom_section(page, "Host Intelligence")
        smooth_scroll_panel(page, "#panelBody", 300, steps=15)

        # ═══════════════════════════════════════════════════════
        # ACT 4: DMARC BLIND SPOT (3:30 – 5:00)
        # Triad, UT-Battelle, LLNS
        # ═══════════════════════════════════════════════════════
        print("Act 4: DMARC Blind Spot")

        # 3:30 — "A finding that may be the most operationally significant..."
        wait_until(t0, T["dmarc_finding"] - 3)
        fade_to_black(page)
        show_title_card(page, "\u25c6  FINDING OF NOTE",
                        "EMAIL AUTHENTICATION",
                        "Management Company DMARC Gap", hold_sec=2.0)
        fade_from_black(page)

        # Navigate directly to Triad National Security
        wait_until(t0, T["triad_manages"] - 5)
        snap(page, t0, "07_before_triad")
        open_contractor(page, TRIAD_IDX, fly=True, fly_zoom=10, fly_duration=2.0)
        scroll_panel_to_top(page)

        # Scroll to DNS/Infrastructure section to show DMARC
        smooth_scroll_to(page, "#panelBody", "Infrastructure")
        highlight_section(page, "Infrastructure")
        zoom_section(page, "Infrastructure", scale=1.15)

        # 4:50 — "The laboratory .gov domains are hardened..."
        wait_until(t0, T["lab_hardened"])
        unzoom_section(page, "Infrastructure")

        # ═══════════════════════════════════════════════════════
        # ACT 5: FULL PICTURE + IMPLICATIONS (5:00 – 8:20)
        # Attack surface stats, then strategic implications
        # ═══════════════════════════════════════════════════════
        print("Act 5: The Full Picture")

        # 5:00 — "Let me put the full picture in front of you."
        wait_until(t0, T["full_picture"] - 5)
        fade_to_black(page)
        show_title_card(page, "\u25c6  ASSESSMENT",
                        "ATTACK SURFACE",
                        "The Full Picture", hold_sec=2.0)
        fade_from_black(page)

        # Close panel, show full map with threat dashboard
        page.keyboard.press("Escape")
        wait(3)

        # Hold on threat dashboard during the stats recitation
        # 5:00–6:29 — all the numbers (1,460 exposed, 237 CVEs, etc.)
        snap(page, t0, "09_threat_dashboard")
        wait_until(t0, T["not_projection"])

        # 6:29 — "This is not a projection..." → heat map
        try:
            page.locator("#heatmapToggle").click(timeout=3000)
            wait(2)
        except Exception:
            pass

        # 6:49–8:20 — implications (foreign intelligence, supply chain, DMARC highway)
        # Hold on heat map — the geographic spread reinforces the "scale" argument
        wait_until(t0, T["how_we_built"] - 3)

        # Turn off heat map before pipeline section
        try:
            page.locator("#heatmapToggle").click(timeout=3000)
            wait(1)
        except Exception:
            pass

        # ═══════════════════════════════════════════════════════
        # ACT 6: PIPELINE (8:20 – 10:46)
        # "So — how did we get all of this?"
        # Show 4 quad-panel images
        # ═══════════════════════════════════════════════════════
        print("Act 6: The Pipeline")

        wait_until(t0, T["how_we_built"])
        fade_to_black(page)
        show_title_card(page, "\u25c6  METHODOLOGY",
                        "14-LAYER PIPELINE",
                        "Automated Open-Source Collection", hold_sec=2.0)
        fade_from_black(page)

        panels_available = all(os.path.exists(p) for p in PANEL_IMAGES.values())

        if panels_available:
            # Panel 1: Discovery (layers 1-4) — 8:31 to ~9:16
            wait_until(t0, T["domain_discovery"] - 2)
            show_image_overlay(page, PANEL_IMAGES["discovery"], fade_in_ms=800)
            snap(page, t0, "11_panel1_discovery")
            wait_until(t0, T["ct_queries"] - 2)
            hide_image_overlay(page, fade_out_ms=500)

            # Panel 2: Infrastructure (layers 5-8) — 9:16 to ~9:56
            show_image_overlay(page, PANEL_IMAGES["infrastructure"], fade_in_ms=800)
            wait_until(t0, T["asn_enum"] - 2)
            hide_image_overlay(page, fade_out_ms=500)

            # Panel 3: Classification (layers 9-12) — 9:56 to ~10:21
            show_image_overlay(page, PANEL_IMAGES["classification"], fade_in_ms=800)
            wait_until(t0, T["nvd_scoring"] + 15)
            hide_image_overlay(page, fade_out_ms=500)

            # Panel 4: Synthesis (layers 13-14) — 10:21 to ~10:46
            show_image_overlay(page, PANEL_IMAGES["synthesis"], fade_in_ms=800)
            wait_until(t0, T["produced_everything"])
            hide_image_overlay(page, fade_out_ms=500)
        else:
            print("  Panel images not found — holding on map")
            wait_until(t0, T["produced_everything"])

        # ═══════════════════════════════════════════════════════
        # ACT 7: CONCLUSION (10:46 – 13:30)
        # "The data shows something..." + four alarming points
        # ═══════════════════════════════════════════════════════
        print("Act 7: Conclusion")

        wait_until(t0, T["data_shows"] - 2)
        fade_to_black(page, duration_ms=500)
        show_title_card(page, "\u25c6  ASSESSMENT",
                        "CONCLUSIONS", "", hold_sec=1.5)
        fade_from_black(page)

        # Show heat map during conclusion
        try:
            page.locator("#heatmapToggle").click(timeout=3000)
            wait(2)
        except Exception:
            pass
        snap(page, t0, "13_conclusion_heatmap")

        # Hold through the four alarming points
        # 11:31–12:46 — "Four things... First... Second... Third..."
        wait_until(t0, T["fourth_scale"] + 10)

        # "This assessment was conducted entirely from open sources..."
        wait_until(t0, T["assessment_conducted"])
        cinematic_fly(page, 39.5, -98.0, 4, duration_sec=3.0)

        # "Classification: unclassified..."
        wait_until(t0, T["classification"])
        wait(10)

        # Final fade to black — hold long enough for audio to finish
        fade_to_black(page, duration_ms=2000)
        # Audio is 810.6s — ensure recording runs past that with padding
        wait_until(t0, 820)
        wait(5)

        total_elapsed = elapsed(t0)
        print(f"Recording complete. Total: {int(total_elapsed)//60}:{int(total_elapsed)%60:02d}")

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
