#!/usr/bin/env python3
"""
Record each act as a separate video, merge with its audio, then concatenate.

Each act is a self-contained video+audio clip. No timestamp estimation.
The screen recording duration naturally matches the visual content,
and the per-act audio is merged immediately. Then ffmpeg concat joins
all 7 acts (+ Veo opening/closing) into the final video.

Usage:
  1. Start server: python3 test_atlas_server.py
  2. Generate audio: python3 generate_act_audio.py
  3. Record: python3 record_per_act.py
  4. Output: videos/osint_atlas_final.mp4
"""

import os
import subprocess
import time
from playwright.sync_api import sync_playwright
from video_transitions import (
    wait, inject_transition_styles, fade_to_black, fade_from_black,
    show_title_card, smooth_scroll_to, smooth_scroll_panel,
    highlight_section, cinematic_fly,
    show_image_overlay, hide_image_overlay,
    open_contractor, zoom_section, unzoom_section, ensure_dark_background,
)

BASE_URL = "http://127.0.0.1:8000"
VIDEO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "videos")
ACTS_DIR = os.path.join(VIDEO_DIR, "audio", "acts")
ACTS_VIDEO_DIR = os.path.join(VIDEO_DIR, "acts")
PANELS_DIR = os.path.join(VIDEO_DIR, "panels")
CLIPS_DIR = os.path.join(VIDEO_DIR, "veo_clips")

PANEL_IMAGES = {
    "discovery":      os.path.join(PANELS_DIR, "panel1_discovery.jpg"),
    "infrastructure": os.path.join(PANELS_DIR, "panel2_infrastructure.jpg"),
    "classification": os.path.join(PANELS_DIR, "panel3_classification.jpg"),
    "synthesis":      os.path.join(PANELS_DIR, "panel4_synthesis.jpg"),
}

FOUR_RIVERS_IDX = 199
UC_REGENTS_IDX = 7
TRIAD_IDX = 10


def get_duration(path):
    result = subprocess.run([
        "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
        "-of", "csv=p=0", path,
    ], capture_output=True, text=True)
    return float(result.stdout.strip())


def open_console(page):
    page.evaluate("() => { if (!atlasChatOpen) toggleAtlasChat(); }")
    wait(1)


def close_console(page):
    page.evaluate("() => { if (atlasChatOpen) toggleAtlasChat(); }")
    wait(0.5)


def send_chat(page, query, wait_seconds=25):
    try:
        input_el = page.locator("#atlasChatInput")
        input_el.click(force=True)
        input_el.fill("")
        for char in query:
            input_el.type(char, delay=30)
        wait(0.3)
        page.keyboard.press("Enter")
        wait(wait_seconds)
    except Exception as e:
        print(f"  Chat error: {e}")
        wait(wait_seconds)


def type_slowly(page, selector, text, delay_ms=30):
    el = page.locator(selector)
    el.click(force=True)
    el.fill("")
    for char in text:
        el.type(char, delay=delay_ms)


def scroll_panel_to_top(page):
    page.evaluate("() => { const p = document.querySelector('#panelBody'); if (p) p.scrollTop = 0; }")
    wait(0.3)


def merge_act(act_name, audio_dur):
    """Merge an act's video with its audio using ffmpeg."""
    video_path = os.path.join(ACTS_VIDEO_DIR, f"{act_name}.webm")
    audio_path = os.path.join(ACTS_DIR, f"{act_name}.mp3")
    output_path = os.path.join(ACTS_VIDEO_DIR, f"{act_name}_merged.mp4")

    if not os.path.exists(audio_path):
        # No audio — just convert to mp4
        subprocess.run([
            "ffmpeg", "-y", "-i", video_path,
            "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-an",
            output_path,
        ], capture_output=True)
        return output_path

    result = subprocess.run([
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        "-movflags", "+faststart",
        output_path,
    ], capture_output=True, text=True)

    if result.returncode != 0:
        print(f"    Merge error: {result.stderr[:200]}")
        return None

    dur = get_duration(output_path)
    size = os.path.getsize(output_path) / 1024 / 1024
    print(f"    Merged: {output_path} ({dur:.0f}s, {size:.1f} MB)")
    return output_path


def main():
    os.makedirs(ACTS_VIDEO_DIR, exist_ok=True)

    # Get audio durations to calibrate visual hold times
    act_audio = {}
    for name in ["act1_hook", "act2_findings", "act3_attack", "act4_dmarc",
                 "act5_surface", "act6_pipeline", "act7_conclusion"]:
        path = os.path.join(ACTS_DIR, f"{name}.mp3")
        if os.path.exists(path):
            act_audio[name] = get_duration(path)
            print(f"  {name}: {act_audio[name]:.1f}s audio")

    with sync_playwright() as p:
        print("\nLaunching browser...")
        browser = p.chromium.launch(headless=False)

        # Load the app once — keep the page alive across all acts
        # We'll create new recording contexts for each act
        # but reuse the same page/tab

        # First, create a non-recording context to load the app
        setup_context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
        )
        page = setup_context.new_page()
        ensure_dark_background(page)
        page.goto(f"{BASE_URL}/atlas", wait_until="networkidle")
        wait(3)
        inject_transition_styles(page)
        setup_context.close()

        # ── RECORD EACH ACT ──

        def record_act(act_name, act_fn, audio_dur):
            """Record a single act with its own video context."""
            print(f"\n{'='*50}")
            print(f"Recording: {act_name} (audio: {audio_dur:.0f}s)")

            record_dir = os.path.join(ACTS_VIDEO_DIR, f"{act_name}_tmp")
            os.makedirs(record_dir, exist_ok=True)

            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                record_video_dir=record_dir,
                record_video_size={"width": 1920, "height": 1080},
            )
            pg = context.new_page()
            ensure_dark_background(pg)
            pg.goto(f"{BASE_URL}/atlas", wait_until="networkidle")
            wait(2)
            inject_transition_styles(pg)

            # Run the act's visual choreography
            act_fn(pg, audio_dur)

            # Save video
            dst = os.path.join(ACTS_VIDEO_DIR, f"{act_name}.webm")
            pg.close()
            pg.video.save_as(dst)
            context.close()

            size = os.path.getsize(dst) / 1024 / 1024
            dur = get_duration(dst)
            print(f"  Recorded: {dst} ({dur:.0f}s, {size:.1f} MB)")

            # Merge with audio
            return merge_act(act_name, audio_dur)

        # ── ACT 1: THE HOOK ──
        def act1_hook(page, audio_dur):
            fade_to_black(page, duration_ms=50)
            wait(0.5)
            show_title_card(page, "OSINT ATLAS",
                            "DOE CONTRACTOR ATTACK SURFACE",
                            "UNCLASSIFIED // FOR OFFICIAL USE ONLY",
                            hold_sec=3.0)
            fade_from_black(page, duration_ms=1500)
            wait(15)  # Map overview

            open_console(page)
            wait(2)
            type_slowly(page, "#atlasChatInput",
                        "show me contractors with critical exposed services")
            wait(0.5)
            page.keyboard.press("Enter")
            wait(15)  # LLM response + map fly

            close_console(page)
            wait(max(0, audio_dur - 42))  # Fill remaining time

        # ── ACT 2: FOUR RIVERS ──
        def act2_findings(page, audio_dur):
            close_console(page)
            open_contractor(page, FOUR_RIVERS_IDX, fly=True, fly_zoom=10, fly_duration=2.0)
            close_console(page)
            scroll_panel_to_top(page)
            wait(5)

            smooth_scroll_to(page, "#panelBody", "Shodan")
            highlight_section(page, "Shodan")
            wait(8)

            smooth_scroll_to(page, "#panelBody", "Host Intelligence")
            highlight_section(page, "Host Intelligence")
            zoom_section(page, "Host Intelligence", scale=1.15)
            wait(12)

            unzoom_section(page, "Host Intelligence")
            smooth_scroll_to(page, "#panelBody", "Dangerous")
            highlight_section(page, "Dangerous")
            zoom_section(page, "Dangerous", scale=1.15)
            wait(10)
            unzoom_section(page, "Dangerous")

            smooth_scroll_panel(page, "#panelBody", 200)
            wait(max(0, audio_dur - 45))

        # ── ACT 3: ATTACK PATH ──
        def act3_attack(page, audio_dur):
            # Start with Four Rivers already visible — open it again
            close_console(page)
            open_contractor(page, FOUR_RIVERS_IDX, fly=True, fly_zoom=10, fly_duration=1.5)
            close_console(page)

            # Kill chain via console
            open_console(page)
            send_chat(page, "generate a kill chain for Four Rivers Nuclear",
                      wait_seconds=30)
            close_console(page)

            smooth_scroll_panel(page, "#panelBody", 400, steps=20)
            wait(8)

            # UC Regents
            open_contractor(page, UC_REGENTS_IDX, fly=True, fly_zoom=10, fly_duration=2.0)
            close_console(page)
            scroll_panel_to_top(page)
            wait(3)

            smooth_scroll_to(page, "#panelBody", "Host Intelligence")
            highlight_section(page, "Host Intelligence")
            zoom_section(page, "Host Intelligence", scale=1.15)
            wait(12)
            unzoom_section(page, "Host Intelligence")
            smooth_scroll_panel(page, "#panelBody", 300, steps=15)
            wait(max(0, audio_dur - 70))

        # ── ACT 4: DMARC ──
        def act4_dmarc(page, audio_dur):
            close_console(page)
            open_contractor(page, TRIAD_IDX, fly=True, fly_zoom=8, fly_duration=2.0)
            close_console(page)
            scroll_panel_to_top(page)
            wait(5)

            smooth_scroll_to(page, "#panelBody", "Infrastructure")
            highlight_section(page, "Infrastructure")
            zoom_section(page, "Infrastructure", scale=1.15)
            wait(35)
            unzoom_section(page, "Infrastructure")
            smooth_scroll_panel(page, "#panelBody", 150)
            wait(max(0, audio_dur - 50))

        # ── ACT 5: ATTACK SURFACE ──
        def act5_surface(page, audio_dur):
            close_console(page)
            page.keyboard.press("Escape")
            wait(1)
            cinematic_fly(page, 39.5, -98.0, 4, duration_sec=2.0)
            wait(55)  # Stats recitation on map

            try:
                page.locator("#heatmapToggle").click(timeout=3000)
                wait(2)
            except Exception:
                pass
            wait(max(0, audio_dur - 70))  # Implications on heat map

            try:
                page.locator("#heatmapToggle").click(timeout=3000)
                wait(1)
            except Exception:
                pass

        # ── ACT 6: PIPELINE ──
        def act6_pipeline(page, audio_dur):
            panels_available = all(os.path.exists(p) for p in PANEL_IMAGES.values())
            if panels_available:
                per_panel = (audio_dur - 10) / 4  # Divide time across 4 panels
                show_image_overlay(page, PANEL_IMAGES["discovery"], fade_in_ms=800)
                wait(per_panel)
                hide_image_overlay(page, fade_out_ms=500)

                show_image_overlay(page, PANEL_IMAGES["infrastructure"], fade_in_ms=800)
                wait(per_panel)
                hide_image_overlay(page, fade_out_ms=500)

                show_image_overlay(page, PANEL_IMAGES["classification"], fade_in_ms=800)
                wait(per_panel)
                hide_image_overlay(page, fade_out_ms=500)

                show_image_overlay(page, PANEL_IMAGES["synthesis"], fade_in_ms=800)
                wait(per_panel)
                hide_image_overlay(page, fade_out_ms=500)
            else:
                wait(audio_dur)

        # ── ACT 7: CONCLUSION ──
        def act7_conclusion(page, audio_dur):
            try:
                page.locator("#heatmapToggle").click(timeout=3000)
                wait(2)
            except Exception:
                pass

            wait(audio_dur - 25)  # Hold on heat map

            cinematic_fly(page, 39.5, -98.0, 4, duration_sec=3.0)
            wait(10)

            fade_to_black(page, duration_ms=2000)
            wait(8)

        # ── RUN ALL ACTS ──
        acts = [
            ("act1_hook", act1_hook),
            ("act2_findings", act2_findings),
            ("act3_attack", act3_attack),
            ("act4_dmarc", act4_dmarc),
            ("act5_surface", act5_surface),
            ("act6_pipeline", act6_pipeline),
            ("act7_conclusion", act7_conclusion),
        ]

        merged_files = []
        for act_name, act_fn in acts:
            audio_dur = act_audio.get(act_name, 60)
            result = record_act(act_name, act_fn, audio_dur)
            if result:
                merged_files.append(result)

        browser.close()

    # ── CONCATENATE ALL ACTS ──
    print(f"\n{'='*50}")
    print("Concatenating all acts...")

    concat_list = os.path.join(VIDEO_DIR, "acts_concat.txt")
    with open(concat_list, "w") as f:
        # Veo opening (if exists)
        veo_opening = os.path.join(CLIPS_DIR, "opening_1080.mp4")
        if os.path.exists(veo_opening):
            f.write(f"file '{veo_opening}'\n")
        elif os.path.exists(os.path.join(CLIPS_DIR, "opening.mp4")):
            # Scale it
            src = os.path.join(CLIPS_DIR, "opening.mp4")
            subprocess.run([
                "ffmpeg", "-y", "-i", src,
                "-vf", "scale=1920:1080:flags=lanczos,setsar=1",
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-c:a", "aac", "-b:a", "128k",
                veo_opening,
            ], capture_output=True)
            f.write(f"file '{veo_opening}'\n")

        # All act clips
        for path in merged_files:
            f.write(f"file '{path}'\n")

        # Veo closing (if exists)
        veo_closing = os.path.join(CLIPS_DIR, "closing_1080.mp4")
        if os.path.exists(veo_closing):
            f.write(f"file '{veo_closing}'\n")
        elif os.path.exists(os.path.join(CLIPS_DIR, "closing.mp4")):
            src = os.path.join(CLIPS_DIR, "closing.mp4")
            subprocess.run([
                "ffmpeg", "-y", "-i", src,
                "-vf", "scale=1920:1080:flags=lanczos,setsar=1",
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-c:a", "aac", "-b:a", "128k",
                veo_closing,
            ], capture_output=True)
            f.write(f"file '{veo_closing}'\n")

    output = os.path.join(VIDEO_DIR, "osint_atlas_final.mp4")
    result = subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        output,
    ], capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Concat error: {result.stderr[:300]}")
        return

    dur = get_duration(output)
    size = os.path.getsize(output) / 1024 / 1024

    print(f"\n{'='*50}")
    print(f"FINAL VIDEO: {output}")
    print(f"  Duration: {int(dur)//60}:{int(dur)%60:02d}")
    print(f"  Size: {size:.1f} MB")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
