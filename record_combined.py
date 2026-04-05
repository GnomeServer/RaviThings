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

# ── Audio timestamps for GEMINI TTS (~655s / 10:55 total) ──
# Calculated from character positions against Gemini Enceladus voice.
# Visual actions fire 2-3s before each timestamp to settle before narration.
AUDIO_DURATION = 655  # seconds
T = {
    "platform_takes":    29,   # 0:29 — "The platform takes plain English"
    "show_me":           34,   # 0:34 — "Show me contractors with critical"
    "four_rivers":       46,   # 0:46 — "This is Four Rivers Nuclear"
    "on_single_ip":      56,   # 0:56 — "On a single IP address"
    "three_databases":   82,   # 1:22 — "Three database engines"
    "attack_path":       97,   # 1:37 — "the system generates an attack path"
    "uc_regents":       131,   # 2:11 — "A second example. UC system"
    "fourteen_year_ssh":164,   # 2:44 — "A fourteen-year-old SSH"
    "dmarc_finding":    169,   # 2:49 — "A finding that may be"
    "triad_manages":    193,   # 3:13 — "Triad National Security manages"
    "lab_hardened":     234,   # 3:54 — "The lab .gov domains are hardened"
    "full_picture":     242,   # 4:02 — "Let me put the full picture"
    "not_projection":   314,   # 5:14 — "This is not a projection"
    "what_means":       331,   # 5:31 — "What that means in practice"
    "supply_chain":     395,   # 6:35 — "The supply chain is the perimeter"
    "how_we_built":     404,   # 6:44 — "So — how did we get all of this"
    "domain_discovery": 413,   # 6:53 — "It starts with domain discovery"
    "ct_queries":       449,   # 7:29 — "Certificate transparency queries"
    "asn_enum":         482,   # 8:02 — "ASN enumeration"
    "nvd_scoring":      502,   # 8:22 — "NVD scoring"
    "produced_everything":522, # 8:42 — "That is what produced everything"
    "data_shows":       525,   # 8:45 — "The data shows something"
    "four_things":      558,   # 9:18 — "Four things make this genuinely"
    "first_supply":     563,   # 9:23 — "First — the supply chain"
    "second_dmarc":     582,   # 9:42 — "Second — the DMARC gap"
    "third_observable": 604,   # 10:04 — "Third — the exposure"
    "fourth_scale":     619,   # 10:19 — "Fourth — scale defeats"
    "assessment_conducted":637,# 10:37 — "This assessment was conducted"
    "classification":   647,   # 10:47 — "Classification: unclassified"
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
TRANSITION_LOG = os.path.join(VIDEO_DIR, "transition_timestamps.txt")
_transitions = []  # (timestamp_sec, act_name)


def mark_transition(t0, act_name):
    """Record the exact timestamp where an act's visual begins."""
    sec = time.time() - t0
    _transitions.append((sec, act_name))
    print(f"  MARK [{int(sec)//60}:{int(sec)%60:02d}] {act_name}")


def save_transitions():
    """Save all transition timestamps to a file for the compositing script."""
    with open(TRANSITION_LOG, "w") as f:
        for sec, name in _transitions:
            f.write(f"{sec:.3f}\t{name}\n")
    print(f"  Transitions saved: {TRANSITION_LOG}")


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
        panel = page.locator("#atlasChatPanel")
        if not panel.is_visible():
            page.locator("#atlasChatToggle").click(timeout=5000)
            wait(1)
    except Exception:
        pass


def close_console(page):
    """Close the command console if it's open."""
    try:
        panel = page.locator("#atlasChatPanel")
        if panel.is_visible():
            page.locator("#atlasChatToggle").click(timeout=3000)
            wait(0.5)
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
    """Video-first recording with transition markers.

    The video is the master clock. Each act gets generous visual time.
    mark_transition() records the exact timestamp where each act begins.
    A separate compositing step places per-act audio at those timestamps.
    """
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

        # ── INTRO ──
        fade_to_black(page, duration_ms=50)
        wait(1)
        show_title_card(page, "OSINT ATLAS",
                        "DOE CONTRACTOR ATTACK SURFACE",
                        "UNCLASSIFIED // FOR OFFICIAL USE ONLY",
                        hold_sec=3.0)
        fade_from_black(page, duration_ms=1500)

        t0 = time.time()
        print("Clock started.")

        # ═══════════════════════════════════════════════════════
        # ACT 1: THE HOOK (~60s of visual time)
        # ═══════════════════════════════════════════════════════
        print("Act 1: The Hook")
        mark_transition(t0, "act1_hook")

        # Hold on map overview — let the viewer see the scale
        wait(25)

        # Open console, type query
        open_console(page)
        wait(2)
        type_slowly(page, "#atlasChatInput",
                    "show me contractors with critical exposed services", delay_ms=30)
        wait(0.5)
        page.keyboard.press("Enter")
        wait(15)  # Wait for LLM + map fly animation

        # Close console so detail panel is visible
        close_console(page)
        wait(5)

        # ═══════════════════════════════════════════════════════
        # ACT 2: FOUR RIVERS (~65s of visual time)
        # ═══════════════════════════════════════════════════════
        print("Act 2: Four Rivers")
        fade_to_black(page)
        show_title_card(page, "\u25c6  CASE STUDY",
                        "FOUR RIVERS NUCLEAR",
                        "$462M DOE Obligations \u00b7 Paducah Plant",
                        hold_sec=2.0)
        fade_from_black(page)
        mark_transition(t0, "act2_findings")

        # Fly directly to Four Rivers, open detail panel
        open_contractor(page, FOUR_RIVERS_IDX, fly=True, fly_zoom=10, fly_duration=2.0)
        close_console(page)  # Ensure console is closed
        scroll_panel_to_top(page)
        wait(8)

        # Scroll to Shodan section
        smooth_scroll_to(page, "#panelBody", "Shodan")
        highlight_section(page, "Shodan")
        wait(8)

        # Host Intelligence — service details
        smooth_scroll_to(page, "#panelBody", "Host Intelligence")
        highlight_section(page, "Host Intelligence")
        zoom_section(page, "Host Intelligence", scale=1.15)
        wait(12)

        # Dangerous Services
        unzoom_section(page, "Host Intelligence")
        smooth_scroll_to(page, "#panelBody", "Dangerous")
        highlight_section(page, "Dangerous")
        zoom_section(page, "Dangerous", scale=1.15)
        wait(10)
        unzoom_section(page, "Dangerous")

        # Hosting attribution
        smooth_scroll_panel(page, "#panelBody", 200)
        wait(8)

        # ═══════════════════════════════════════════════════════
        # ACT 3: ATTACK PATH (~95s of visual time)
        # ═══════════════════════════════════════════════════════
        print("Act 3: Attack Path")
        fade_to_black(page)
        show_title_card(page, "\u25c6  ATTACK PATH",
                        "MITRE ATT&CK KILL CHAIN",
                        "Automated from Observed Services",
                        hold_sec=2.0)
        fade_from_black(page)
        mark_transition(t0, "act3_attack")

        # Open console for kill chain query
        open_console(page)
        send_chat(page, "generate a kill chain for Four Rivers Nuclear",
                  wait_seconds=35)
        close_console(page)

        # Scroll through kill chain result
        smooth_scroll_panel(page, "#panelBody", 400, steps=20)
        wait(10)

        # UC Regents — fly directly
        open_contractor(page, UC_REGENTS_IDX, fly=True, fly_zoom=10, fly_duration=2.0)
        close_console(page)
        scroll_panel_to_top(page)
        wait(3)

        # Show their Host Intelligence
        smooth_scroll_to(page, "#panelBody", "Host Intelligence")
        highlight_section(page, "Host Intelligence")
        zoom_section(page, "Host Intelligence", scale=1.15)
        wait(15)
        unzoom_section(page, "Host Intelligence")
        smooth_scroll_panel(page, "#panelBody", 300, steps=15)
        wait(8)

        # ═══════════════════════════════════════════════════════
        # ACT 4: DMARC (~90s of visual time)
        # ═══════════════════════════════════════════════════════
        print("Act 4: DMARC")
        fade_to_black(page)
        show_title_card(page, "\u25c6  FINDING OF NOTE",
                        "EMAIL AUTHENTICATION",
                        "Management Company DMARC Gap",
                        hold_sec=2.0)
        fade_from_black(page)
        mark_transition(t0, "act4_dmarc")

        # Navigate to Triad National Security
        open_contractor(page, TRIAD_IDX, fly=True, fly_zoom=8, fly_duration=2.0)
        close_console(page)
        scroll_panel_to_top(page)
        wait(5)

        # Show DNS/Infrastructure section with DMARC
        smooth_scroll_to(page, "#panelBody", "Infrastructure")
        highlight_section(page, "Infrastructure")
        zoom_section(page, "Infrastructure", scale=1.15)
        wait(40)

        # Hold on DMARC display
        unzoom_section(page, "Infrastructure")
        smooth_scroll_panel(page, "#panelBody", 150)
        wait(25)

        # ═══════════════════════════════════════════════════════
        # ACT 5: ATTACK SURFACE (~145s of visual time)
        # ═══════════════════════════════════════════════════════
        print("Act 5: Attack Surface")
        fade_to_black(page)
        show_title_card(page, "\u25c6  ASSESSMENT",
                        "ATTACK SURFACE",
                        "The Full Picture",
                        hold_sec=2.0)
        fade_from_black(page)
        mark_transition(t0, "act5_surface")

        # Close everything — clean full map with threat dashboard
        page.keyboard.press("Escape")
        wait(1)
        close_console(page)
        cinematic_fly(page, 39.5, -98.0, 4, duration_sec=2.0)
        wait(60)  # Stats recitation — hold on map/dashboard

        # Heat map for "not a projection" / implications section
        try:
            page.locator("#heatmapToggle").click(timeout=3000)
            wait(2)
        except Exception:
            pass
        wait(70)  # Hold on heat map through implications

        # Turn off heat map
        try:
            page.locator("#heatmapToggle").click(timeout=3000)
            wait(2)
        except Exception:
            pass

        # ═══════════════════════════════════════════════════════
        # ACT 6: PIPELINE (~115s of visual time)
        # ═══════════════════════════════════════════════════════
        print("Act 6: Pipeline")
        fade_to_black(page)
        show_title_card(page, "\u25c6  METHODOLOGY",
                        "14-LAYER PIPELINE",
                        "Automated Open-Source Collection",
                        hold_sec=2.0)
        fade_from_black(page)
        mark_transition(t0, "act6_pipeline")

        panels_available = all(os.path.exists(p) for p in PANEL_IMAGES.values())

        if panels_available:
            # Panel 1: Discovery (layers 1-4)
            show_image_overlay(page, PANEL_IMAGES["discovery"], fade_in_ms=800)
            wait(28)
            hide_image_overlay(page, fade_out_ms=500)

            # Panel 2: Infrastructure (layers 5-8)
            show_image_overlay(page, PANEL_IMAGES["infrastructure"], fade_in_ms=800)
            wait(25)
            hide_image_overlay(page, fade_out_ms=500)

            # Panel 3: Classification (layers 9-12)
            show_image_overlay(page, PANEL_IMAGES["classification"], fade_in_ms=800)
            wait(22)
            hide_image_overlay(page, fade_out_ms=500)

            # Panel 4: Synthesis (layers 13-14)
            show_image_overlay(page, PANEL_IMAGES["synthesis"], fade_in_ms=800)
            wait(22)
            hide_image_overlay(page, fade_out_ms=500)
        else:
            print("  Panel images not found — holding on map")
            wait(100)

        wait(5)

        # ═══════════════════════════════════════════════════════
        # ACT 7: CONCLUSION (~150s of visual time)
        # ═══════════════════════════════════════════════════════
        print("Act 7: Conclusion")
        fade_to_black(page, duration_ms=500)
        show_title_card(page, "\u25c6  ASSESSMENT",
                        "CONCLUSIONS", "",
                        hold_sec=1.5)
        fade_from_black(page)
        mark_transition(t0, "act7_conclusion")

        # Heat map during conclusion
        try:
            page.locator("#heatmapToggle").click(timeout=3000)
            wait(2)
        except Exception:
            pass

        # Hold through four alarming points + close
        wait(120)

        # Cinematic zoom out
        cinematic_fly(page, 39.5, -98.0, 4, duration_sec=3.0)
        wait(15)

        # Final fade to black
        fade_to_black(page, duration_ms=2000)
        wait(10)

        total_elapsed = elapsed(t0)
        print(f"Recording complete. Total: {int(total_elapsed)//60}:{int(total_elapsed)%60:02d}")

        # Save transitions for compositing
        save_transitions()

        # ── Save video ──
        dst = os.path.join(VIDEO_DIR, "osint_atlas_briefing.webm")
        page.close()
        page.video.save_as(dst)
        context.close()
        browser.close()
        size = os.path.getsize(dst)
        print(f"Saved: {dst} ({size / 1024 / 1024:.1f} MB)")

    print("\nVideo recorded. Run composite_act_audio.py to add per-act audio.")


if __name__ == "__main__":
    main()
