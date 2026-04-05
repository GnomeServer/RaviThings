#!/usr/bin/env python3
"""
Generate voiceover audio for OSINT Atlas demo videos using ElevenLabs TTS.

Reads narration scripts, generates MP3 audio via ElevenLabs API,
then merges audio with video recordings using ffmpeg.

Prerequisites:
  - ELEVENLABS_API_KEY in .env
  - pip install elevenlabs
  - ffmpeg installed
  - Video recordings in videos/ directory

Usage:
  python3 generate_voiceover.py [--video 1|2|3|4|5|all] [--test]
"""

import argparse
import os
import subprocess

from dotenv import load_dotenv

load_dotenv()

from elevenlabs.client import ElevenLabs

# Voice settings — choose one:
# "nPczCjzI2devNBz1zQrb"  Brian — Deep, Resonant (Pentagon briefer)
# "XrExE9yKIg1WjnnlVkGX"  Matilda — Professional, Knowledgeable (intel analyst)
# "pNInz6obpgDQGcFmaJgB"  Adam — Dominant, Firm (command authority)
VOICE_ID = "nPczCjzI2devNBz1zQrb"  # Brian — deep, resonant
MODEL_ID = "eleven_v3"
OUTPUT_FORMAT = "mp3_44100_128"

AUDIO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "videos", "audio")
VIDEO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "videos")

# Narration scripts for each video — written to match the screen recording timing
NARRATIONS = {
    "combined": {
        "name": "osint_atlas_briefing",
        "text": open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "videos", "combined_narration_tts.txt")).read(),
    },
    "1": {
        "name": "video_1_the_scale",
        "text": (
            "This is every DOE contractor in the United States. "
            "Two thousand two hundred and fourteen organizations. "
            "One hundred twenty-seven point six billion dollars in federal obligations. "
            "We mapped their entire public-facing attack surface from open sources. "
            "Every port. Every vulnerability. Every expired certificate. "
            "Fourteen hundred and sixty-four internet-exposed. "
            "Five hundred thirty-four with critical CVEs. "
            "Over thirteen hundred with no email authentication. "
            "This contractor manages the Pantex Plant, "
            "where every nuclear warhead in the U.S. arsenal is assembled. "
            "We found their attack surface in thirty seconds. "
            "This is what an adversary already knows about the DOE supply chain."
        ),
    },
    "2": {
        "name": "video_2_command_console",
        "text": (
            "No buttons. No menus. Type a question in plain English "
            "and the system finds the answer. "
            "Show me contractors with critical exposed services. "
            "The map filters instantly. "
            "Which one has the most exposed services? "
            "A nuclear decommissioning contractor appears "
            "with nine services exposed on a single IP address. "
            "Three databases. Remote desktop. SMB version one. "
            "All on an end-of-life Windows Server. "
            "The AI doesn't just answer questions. It drives the entire map."
        ),
    },
    "3": {
        "name": "video_3_intelligence_brief",
        "text": (
            "DNS probing found G.S.A. e-library dot gov as Centerra's domain. "
            "That's a government catalog site. Completely wrong. "
            "For months, every scan, every vulnerability check, "
            "every certificate lookup hit the wrong target. "
            "The real attack surface was invisible. "
            "The AI researched the company, "
            "found it was acquired by Constellis Holdings, "
            "and corrected the domain to constellis dot com. "
            "Then it automatically re-ran every downstream scan against the real domain. "
            "Nine hundred eighty-seven contractors had wrong domains. "
            "Nine hundred eighty-seven blind spots in our security picture. "
            "The AI found them all."
        ),
    },
    "4": {
        "name": "video_4_kill_chain",
        "text": (
            "Show me the highest risk Research and Labs contractor. "
            "The system identifies the target. "
            "Critical danger level. Hundreds of known vulnerabilities. "
            "Exposed services confirmed by Shodan product banners. "
            "Now, generate a kill chain. "
            "The system maps the attack path to MITRE ATT and CK. "
            "Initial access through the exposed service. "
            "Credential harvesting. Lateral movement. Exfiltration. "
            "Every step cites a real IP address, a real port, a real service. "
            "Not theoretical. Not simulated. "
            "This is what the attack path looks like, right now, "
            "from data anyone can collect."
        ),
    },
    "5": {
        "name": "video_5_phishing_surface",
        "text": (
            "The national lab domains, sandia dot gov, LANL dot gov, ORNL dot gov, "
            "all have DMARC reject. Properly configured. "
            "But the private companies that manage these labs? "
            "We checked their domains live. "
            "Triad National Security, manages Los Alamos, no DMARC. "
            "Lawrence Livermore National Security, manages LLNL, no DMARC. "
            "UT Battelle, manages Oak Ridge, no DMARC. "
            "Thirty-six billion dollars in nuclear security "
            "managed by companies whose email can be spoofed by anyone. "
            "The dot gov is locked. The dot org is wide open. "
            "All from public data. All verifiable right now. Unclassified."
        ),
    },
}


def generate_audio(client, video_num):
    """Generate voiceover audio for a single video.

    Handles text >5000 chars by splitting into chunks at paragraph
    boundaries and concatenating the audio.
    """
    narration = NARRATIONS[video_num]
    name = narration["name"]
    text = narration["text"]

    print(f"  Generating audio for {name}...")
    print(f"  Text length: {len(text)} chars")

    MAX_CHARS = 4500  # ElevenLabs API hard limit is 5000/request on all plans
    audio_path = os.path.join(AUDIO_DIR, f"{name}.mp3")

    if len(text) <= MAX_CHARS:
        # Single request
        audio = client.text_to_speech.convert(
            text=text, voice_id=VOICE_ID,
            model_id=MODEL_ID, output_format=OUTPUT_FORMAT,
        )
        with open(audio_path, "wb") as f:
            for chunk in audio:
                f.write(chunk)
    else:
        # Split into chunks at paragraph boundaries
        paragraphs = text.split("\n\n")
        chunks = []
        current = ""
        for para in paragraphs:
            if len(current) + len(para) + 2 > MAX_CHARS and current:
                chunks.append(current.strip())
                current = para
            else:
                current = current + "\n\n" + para if current else para
        if current.strip():
            chunks.append(current.strip())

        print(f"  Split into {len(chunks)} chunks")

        # Generate audio for each chunk
        chunk_files = []
        for i, chunk in enumerate(chunks):
            print(f"  Chunk {i+1}/{len(chunks)} ({len(chunk)} chars)...")
            audio = client.text_to_speech.convert(
                text=chunk, voice_id=VOICE_ID,
                model_id=MODEL_ID, output_format=OUTPUT_FORMAT,
            )
            chunk_path = os.path.join(AUDIO_DIR, f"{name}_chunk{i}.mp3")
            with open(chunk_path, "wb") as f:
                for c in audio:
                    f.write(c)
            chunk_files.append(chunk_path)

        # Concatenate with ffmpeg
        list_file = os.path.join(AUDIO_DIR, f"{name}_chunks.txt")
        with open(list_file, "w") as f:
            for cf in chunk_files:
                f.write(f"file '{cf}'\n")

        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", list_file, "-c", "copy", audio_path,
        ], capture_output=True)

        # Clean up chunks
        for cf in chunk_files:
            os.unlink(cf)
        os.unlink(list_file)

    size = os.path.getsize(audio_path)
    print(f"  Saved: {audio_path} ({size / 1024:.0f} KB)")
    return audio_path


def merge_audio_video(video_num):
    """Merge audio with video using ffmpeg."""
    narration = NARRATIONS[video_num]
    name = narration["name"]

    video_path = os.path.join(VIDEO_DIR, f"{name}.webm")
    audio_path = os.path.join(AUDIO_DIR, f"{name}.mp3")
    output_path = os.path.join(VIDEO_DIR, f"{name}_final.mp4")

    if not os.path.exists(video_path):
        print(f"  WARNING: Video not found: {video_path}")
        return None

    if not os.path.exists(audio_path):
        print(f"  WARNING: Audio not found: {audio_path}")
        return None

    print(f"  Merging: {name}")

    # Use ffmpeg to combine video + audio
    # -shortest: end when the shorter stream ends
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "libx264",
        "-c:a", "aac",
        "-shortest",
        "-movflags", "+faststart",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ffmpeg error: {result.stderr[:200]}")
        return None

    size = os.path.getsize(output_path)
    print(f"  Final video: {output_path} ({size / 1024 / 1024:.1f} MB)")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate voiceover for demo videos")
    parser.add_argument("--video", default="all", help="Which video: 1-5 or all")
    parser.add_argument("--test", action="store_true", help="Generate only first video for testing")
    parser.add_argument("--audio-only", action="store_true", help="Generate audio without merging")
    args = parser.parse_args()

    os.makedirs(AUDIO_DIR, exist_ok=True)

    client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

    to_process = ["1"] if args.test else (
        list(NARRATIONS.keys()) if args.video == "all" else [args.video]
    )

    # Phase 1: Generate audio
    print("\n=== Phase 1: Generating voiceover audio ===")
    for vid_num in to_process:
        if vid_num not in NARRATIONS:
            print(f"Unknown video: {vid_num}")
            continue
        generate_audio(client, vid_num)

    if args.audio_only:
        print("\nAudio-only mode — skipping merge.")
        return

    # Phase 2: Merge audio + video
    print("\n=== Phase 2: Merging audio with video ===")
    for vid_num in to_process:
        merge_audio_video(vid_num)

    print("\nDone! Final videos in videos/*_final.mp4")


if __name__ == "__main__":
    main()
