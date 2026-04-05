#!/usr/bin/env python3
"""
Generate Veo video clips for the OSINT Atlas briefing.

Creates cinematic B-roll: opening sequence, animated panel images,
transition clips, and closing sequence. Uses Veo 3.1 via Gemini API.

Each clip is 8 seconds. Panel animations use image-to-video to
bring the static quad-panel JPGs to life.

Usage:
  python3 generate_veo_clips.py [--clip opening|panel1|panel2|panel3|panel4|closing|all]
"""

import argparse
import os
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from google import genai
from google.genai import types

VIDEO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "videos")
CLIPS_DIR = os.path.join(VIDEO_DIR, "veo_clips")
PANELS_DIR = os.path.join(VIDEO_DIR, "panels")

# Veo model — use 3.1 for best quality with native audio
MODEL = "veo-3.1-generate-preview"

# Clip definitions
CLIPS = {
    "opening": {
        "prompt": (
            "A dark military command center. Multiple screens flicker to life in sequence, "
            "casting blue-cyan light across the room. The central screen displays a map of "
            "the United States with thousands of glowing cyan dots appearing one by one — "
            "each representing a DOE contractor location. The dots pulse softly. The camera "
            "slowly pushes in toward the central screen. No people visible. Dark navy "
            "lighting. The atmosphere is tense and operational. Subtle electronic hum in "
            "the background. No music. No dialogue."
        ),
        "image": None,
        "duration": "8",
        "resolution": "1080p",
    },
    "panel1": {
        "prompt": (
            "A dark tactical display showing domain names resolving in sequence. "
            "Green checkmarks appear next to successfully resolved domains while red X marks "
            "flash on failures. Thin cyan lines connect company names to their domains. "
            "A counter in the corner ticks up rapidly. The data flows downward like a "
            "cascading waterfall. Dark navy background with cyan accent lighting. "
            "No sound effects. No music. No dialogue."
        ),
        "image": os.path.join(PANELS_DIR, "panel1_discovery.jpg"),
        "duration": "8",
        "resolution": "1080p",
    },
    "panel2": {
        "prompt": (
            "A dark intelligence dashboard showing infrastructure mapping. A radial tree "
            "diagram grows outward from a central domain node, with branches extending to "
            "subdomains that glow in different colors — red for VPN, orange for authentication, "
            "yellow for development. Simultaneously, glowing dots appear on a world map "
            "representing discovered hosts. Service banners populate in a scrolling table. "
            "Dark navy background. Technical HUD aesthetic. No sound effects. No dialogue."
        ),
        "image": os.path.join(PANELS_DIR, "panel2_infrastructure.jpg"),
        "duration": "8",
        "resolution": "1080p",
    },
    "panel3": {
        "prompt": (
            "A dark network classification display. Large translucent circles representing "
            "autonomous systems form and connect with IP address dots inside them. A split "
            "bar fills from left to right showing on-premises versus cloud infrastructure. "
            "A side-by-side comparison slides in showing port-based versus banner-aware "
            "classification. Vulnerability severity bars grow from left to right in red, "
            "orange, yellow, and green. Dark navy background with cyan accents. "
            "No sound effects. No dialogue."
        ),
        "image": os.path.join(PANELS_DIR, "panel3_classification.jpg"),
        "duration": "8",
        "resolution": "1080p",
    },
    "panel4": {
        "prompt": (
            "A dark intelligence synthesis display. Highlighted text entities animate across "
            "a document — organizations in purple, facilities in green, materials in red. "
            "Lines connect them to a categorized sidebar. Then a massive knowledge graph "
            "materializes — thousands of nodes connected by relationship lines, clustering "
            "into visible groups. The graph rotates slowly. Statistics tick up in the corner: "
            "24,706 nodes, 72,064 relationships. Dark navy background. "
            "No sound effects. No dialogue."
        ),
        "image": os.path.join(PANELS_DIR, "panel4_synthesis.jpg"),
        "duration": "8",
        "resolution": "1080p",
    },
    "closing": {
        "prompt": (
            "A slow cinematic pull back from a tactical display showing the United States "
            "covered in glowing heat signatures — red, orange, and yellow concentrations "
            "over major cities and DOE facility locations. The camera pulls back steadily, "
            "revealing the full continental view. The text 'UNCLASSIFIED' stamps onto the "
            "screen with authority in white monospace font. The heat signatures slowly fade. "
            "Dark navy background. Somber. Final. No music. No dialogue."
        ),
        "image": None,
        "duration": "8",
        "resolution": "1080p",
    },
}


def generate_clip(client, name, config):
    """Generate a single Veo clip."""
    print(f"\n{'='*60}")
    print(f"Generating: {name}")
    print(f"  Prompt: {config['prompt'][:80]}...")

    kwargs = {
        "model": MODEL,
        "prompt": config["prompt"],
        "config": types.GenerateVideoConfig(
            aspect_ratio="16:9",
            duration_seconds=int(config["duration"]),
            resolution=config["resolution"],
            person_generation="allow_all",
        ),
    }

    # Image-to-video if source image provided
    if config.get("image") and os.path.exists(config["image"]):
        print(f"  Source image: {config['image']}")
        from google.genai.types import Image
        img = Image.from_file(config["image"])
        kwargs["image"] = img

    # Generate
    print(f"  Submitting to {MODEL}...")
    operation = client.models.generate_videos(**kwargs)

    # Poll for completion
    start = time.time()
    while not operation.done:
        elapsed = time.time() - start
        print(f"  Waiting... ({int(elapsed)}s)")
        time.sleep(10)
        operation = client.operations.get(operation)

        if elapsed > 360:  # 6 minute timeout
            print(f"  TIMEOUT after {int(elapsed)}s")
            return None

    # Download result
    if not operation.response or not operation.response.generated_videos:
        print(f"  ERROR: No video generated")
        if hasattr(operation, 'error') and operation.error:
            print(f"  Error: {operation.error}")
        return None

    video = operation.response.generated_videos[0]
    output_path = os.path.join(CLIPS_DIR, f"{name}.mp4")

    client.files.download(file=video.video)
    video.video.save(output_path)

    size = os.path.getsize(output_path)
    elapsed = time.time() - start
    print(f"  Saved: {output_path} ({size / 1024 / 1024:.1f} MB, {int(elapsed)}s)")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate Veo video clips")
    parser.add_argument("--clip", default="all",
                        help="Which clip: opening, panel1-4, closing, or all")
    args = parser.parse_args()

    os.makedirs(CLIPS_DIR, exist_ok=True)

    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

    if args.clip == "all":
        to_generate = list(CLIPS.keys())
    else:
        to_generate = [args.clip]

    results = {}
    for name in to_generate:
        if name not in CLIPS:
            print(f"Unknown clip: {name}")
            continue
        path = generate_clip(client, name, CLIPS[name])
        results[name] = path

    print(f"\n{'='*60}")
    print("RESULTS:")
    for name, path in results.items():
        status = f"OK ({path})" if path else "FAILED"
        print(f"  {name}: {status}")


if __name__ == "__main__":
    main()
