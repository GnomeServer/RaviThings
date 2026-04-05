#!/usr/bin/env python3
"""
Record OSINT Atlas demo videos using Playwright.

Each video follows the sequence from video_scripts.md.
Output: MP4 files in videos/ directory.

Prerequisites:
  - Server running: python3 test_atlas_server.py
  - Playwright browsers: python3 -m playwright install chromium

Usage:
  python3 record_videos.py [--video 1|2|3|4|5|all] [--url http://localhost:8000]
"""

import argparse
import os
import time
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8000"
VIDEO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "videos")


def wait(seconds):
    """Wait with a visible countdown."""
    time.sleep(seconds)


def type_slowly(page, selector, text, delay=50):
    """Type text character by character for visual effect."""
    el = page.locator(selector)
    el.click()
    el.fill("")
    for char in text:
        el.type(char, delay=delay)


def send_chat(page, query, wait_seconds=25):
    """Type a query into the console and wait for response."""
    input_sel = "#atlasChatInput"
    try:
        type_slowly(page, input_sel, query, delay=40)
    except Exception:
        # Fallback: try textarea
        type_slowly(page, 'textarea', query, delay=40)
    time.sleep(0.5)
    page.keyboard.press("Enter")
    wait(wait_seconds)


def open_console(page):
    """Open the command console if not already open."""
    try:
        page.locator("#atlasChatToggle").click(timeout=5000)
        wait(1)
    except Exception:
        # Try by text content
        try:
            page.get_by_text("⌘").first.click(timeout=3000)
            wait(1)
        except Exception:
            pass


def record_video_1(page):
    """Video 1: The Scale — overview, dashboard, Pantex contractor."""
    print("  Recording Video 1: The Scale")

    # Load the app
    page.goto(f"{BASE_URL}/atlas", wait_until="networkidle")
    wait(10)  # Let map markers and data fully render

    # Hold on full map overview with threat dashboard — the money shot
    wait(5)

    # Open console and ask about a nuclear contractor
    open_console(page)
    wait(1)
    send_chat(page, "show me the contractor that manages the Pantex nuclear weapons plant", wait_seconds=30)

    # Hold on result
    wait(5)

    # Close console to show full map
    page.keyboard.press("Escape")
    wait(5)

    print("  Video 1 complete")


def record_video_2(page):
    """Video 2: The Command Console — natural language queries."""
    print("  Recording Video 2: The Command Console")

    page.goto(f"{BASE_URL}/atlas", wait_until="networkidle")
    wait(10)

    # Open console
    open_console(page)
    wait(1)

    # Query 1: critical exposed services
    send_chat(page, "show me contractors with critical exposed services", wait_seconds=30)

    # Query 2: most exposed
    send_chat(page, "which one has the most exposed services", wait_seconds=30)

    # Hold on result
    wait(5)

    print("  Video 2 complete")


def record_video_3(page):
    """Video 3: The Intelligence Brief — AI research, domain corrections."""
    print("  Recording Video 3: The Intelligence Brief")

    page.goto(f"{BASE_URL}/atlas", wait_until="networkidle")
    wait(10)

    # Search for Centerra
    search = page.locator('input[placeholder*="SEARCH"]')
    search.click()
    search.fill("Centerra")
    wait(1)
    search.press("Enter")
    wait(3)

    # Scroll detail panel to show AI Research Brief
    panel_body = page.locator("#panelBody")
    for _ in range(3):
        panel_body.evaluate("el => el.scrollTop += 300")
        wait(1)

    # Hold on AI Research Brief section
    wait(5)

    # Search for West Publishing
    search.click()
    search.fill("West Publishing")
    wait(1)
    search.press("Enter")
    wait(3)

    # Scroll to AI Research
    for _ in range(3):
        panel_body.evaluate("el => el.scrollTop += 300")
        wait(1)

    wait(5)

    print("  Video 3 complete")


def record_video_4(page):
    """Video 4: The Kill Chain — Four Rivers Nuclear, Table of Horrors."""
    print("  Recording Video 4: The Kill Chain")

    page.goto(f"{BASE_URL}/atlas", wait_until="networkidle")
    wait(10)

    # Open console
    open_console(page)
    wait(1)

    # Query: nuclear contractors with exposed databases
    send_chat(page, "show me the highest risk Research & Labs contractor", wait_seconds=35)

    # Hold on result with exposed services visible
    wait(5)

    # Scroll detail panel to show services
    panel_body = page.locator("#panelBody")
    for _ in range(2):
        panel_body.evaluate("el => el.scrollTop += 250")
        wait(1)

    wait(3)

    # Click Kill Chain button
    try:
        page.locator("button:has-text('Kill Chain')").click(timeout=3000)
        wait(20)  # Wait for kill chain generation
    except Exception:
        pass

    # Hold on kill chain
    wait(5)

    print("  Video 4 complete")


def record_video_5(page):
    """Video 5: The Phishing Surface — management company DMARC gaps."""
    print("  Recording Video 5: The Phishing Surface")

    page.goto(f"{BASE_URL}/atlas", wait_until="networkidle")
    wait(10)

    # Toggle heat map
    try:
        page.locator("button:has-text('Heat Map')").click(timeout=3000)
        wait(5)
    except Exception:
        pass

    # Open console
    open_console(page)
    wait(1)

    # Query about DMARC
    send_chat(page, "show me nuclear lab management companies with no DMARC", wait_seconds=30)

    # Hold on result
    wait(5)

    # Toggle heat map off
    try:
        page.locator("button:has-text('Heat Map')").click(timeout=3000)
        wait(3)
    except Exception:
        pass

    print("  Video 5 complete")


def main():
    parser = argparse.ArgumentParser(description="Record OSINT Atlas demo videos")
    parser.add_argument("--video", default="all", help="Which video to record: 1-5 or all")
    parser.add_argument("--url", default=BASE_URL, help="Server URL")
    args = parser.parse_args()

    pass  # BASE_URL used from module level

    os.makedirs(VIDEO_DIR, exist_ok=True)

    videos = {
        "1": ("video_1_the_scale", record_video_1),
        "2": ("video_2_command_console", record_video_2),
        "3": ("video_3_intelligence_brief", record_video_3),
        "4": ("video_4_kill_chain", record_video_4),
        "5": ("video_5_phishing_surface", record_video_5),
    }

    to_record = list(videos.keys()) if args.video == "all" else [args.video]

    with sync_playwright() as p:
        for vid_num in to_record:
            if vid_num not in videos:
                print(f"Unknown video: {vid_num}")
                continue

            name, record_fn = videos[vid_num]
            video_path = os.path.join(VIDEO_DIR, name)

            print(f"\nRecording {name}...")

            browser = p.chromium.launch(headless=False)
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                record_video_dir=video_path,
                record_video_size={"width": 1920, "height": 1080},
            )
            page = context.new_page()

            try:
                record_fn(page)
            except Exception as e:
                print(f"  ERROR: {e}")
            finally:
                context.close()
                browser.close()

                # Find the recorded video file
                for f in os.listdir(video_path):
                    if f.endswith(".webm"):
                        src = os.path.join(video_path, f)
                        dst = os.path.join(VIDEO_DIR, f"{name}.webm")
                        os.rename(src, dst)
                        print(f"  Saved: {dst}")
                        break

    print(f"\nAll recordings saved to {VIDEO_DIR}/")


if __name__ == "__main__":
    main()
