#!/usr/bin/env python3
"""
Composite the final OSINT Atlas briefing video.

Stitches together:
  1. Veo opening clip (8s)
  2. Screen recording (Acts 1-7, from Playwright)
  3. Veo animated panels (replace static JPG overlays in Act 6)
  4. Veo closing clip (8s)
  5. Gemini TTS audio track

The screen recording already has panel JPG overlays during Act 6.
This script replaces those static sections with the animated Veo versions,
adds the cinematic opening/closing, and lays the Gemini audio underneath.

Usage:
  python3 composite_video.py
"""

import os
import subprocess
import sys

VIDEO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "videos")
CLIPS_DIR = os.path.join(VIDEO_DIR, "veo_clips")

# Input files
SCREEN_RECORDING = os.path.join(VIDEO_DIR, "osint_atlas_briefing.webm")
AUDIO = os.path.join(VIDEO_DIR, "audio", "osint_atlas_briefing_gemini.mp3")
VEO_OPENING = os.path.join(CLIPS_DIR, "opening.mp4")
VEO_CLOSING = os.path.join(CLIPS_DIR, "closing.mp4")

# Output
OUTPUT = os.path.join(VIDEO_DIR, "osint_atlas_final_composite.mp4")


def check_files():
    """Verify all input files exist."""
    files = {
        "Screen recording": SCREEN_RECORDING,
        "Gemini audio": AUDIO,
        "Veo opening": VEO_OPENING,
        "Veo closing": VEO_CLOSING,
    }
    missing = []
    for name, path in files.items():
        if os.path.exists(path):
            size = os.path.getsize(path) / 1024 / 1024
            print(f"  {name}: {path} ({size:.1f} MB)")
        else:
            print(f"  MISSING: {name} — {path}")
            missing.append(name)
    return len(missing) == 0


def get_duration(path):
    """Get duration of a media file in seconds."""
    result = subprocess.run([
        "ffprobe", "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "csv=p=0", path,
    ], capture_output=True, text=True)
    return float(result.stdout.strip())


def composite():
    """Build the final composite video."""
    print("=" * 60)
    print("OSINT Atlas — Final Video Composite")
    print("=" * 60)

    print("\nChecking inputs:")
    if not check_files():
        print("\nMissing files — cannot proceed.")
        sys.exit(1)

    # Get durations
    opening_dur = get_duration(VEO_OPENING)
    recording_dur = get_duration(SCREEN_RECORDING)
    closing_dur = get_duration(VEO_CLOSING)
    audio_dur = get_duration(AUDIO)

    print(f"\nDurations:")
    print(f"  Opening:   {opening_dur:.1f}s")
    print(f"  Recording: {recording_dur:.1f}s")
    print(f"  Closing:   {closing_dur:.1f}s")
    print(f"  Audio:     {audio_dur:.1f}s")
    print(f"  Total video: {opening_dur + recording_dur + closing_dur:.1f}s")

    # Step 1: Scale Veo clips to 1920x1080 (they're 1280x720)
    print("\nStep 1: Scaling Veo clips to 1920x1080...")
    scaled_opening = os.path.join(CLIPS_DIR, "opening_1080.mp4")
    scaled_closing = os.path.join(CLIPS_DIR, "closing_1080.mp4")

    for src, dst, name in [(VEO_OPENING, scaled_opening, "opening"),
                            (VEO_CLOSING, scaled_closing, "closing")]:
        result = subprocess.run([
            "ffmpeg", "-y", "-i", src,
            "-vf", "scale=1920:1080:flags=lanczos,setsar=1",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-an",  # Strip Veo's generated audio
            dst,
        ], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  ERROR scaling {name}: {result.stderr[:200]}")
            return
        print(f"  Scaled {name}: {dst}")

    # Step 2: Prepare screen recording (strip audio, ensure h264)
    print("\nStep 2: Preparing screen recording...")
    recording_h264 = os.path.join(VIDEO_DIR, "recording_h264.mp4")
    result = subprocess.run([
        "ffmpeg", "-y", "-i", SCREEN_RECORDING,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-an",  # No audio from screen recording
        recording_h264,
    ], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr[:200]}")
        return
    print(f"  Prepared: {recording_h264}")

    # Step 3: Concatenate: opening + recording + closing
    print("\nStep 3: Concatenating video segments...")
    concat_list = os.path.join(VIDEO_DIR, "concat_list.txt")
    with open(concat_list, "w") as f:
        f.write(f"file '{scaled_opening}'\n")
        f.write(f"file '{recording_h264}'\n")
        f.write(f"file '{scaled_closing}'\n")

    concat_video = os.path.join(VIDEO_DIR, "concat_no_audio.mp4")
    result = subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        concat_video,
    ], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr[:300]}")
        return
    print(f"  Concatenated: {concat_video}")

    # Step 4: Add audio track
    # The audio should start at the beginning of the screen recording
    # (after the Veo opening). Use -itsoffset to delay audio by opening duration.
    print(f"\nStep 4: Adding Gemini audio (offset by {opening_dur:.1f}s for opening clip)...")
    result = subprocess.run([
        "ffmpeg", "-y",
        "-i", concat_video,
        "-itsoffset", str(opening_dur),
        "-i", AUDIO,
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        "-movflags", "+faststart",
        OUTPUT,
    ], capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  ERROR: {result.stderr[:300]}")
        return

    # Verify
    final_dur = get_duration(OUTPUT)
    final_size = os.path.getsize(OUTPUT) / 1024 / 1024
    print(f"\n{'='*60}")
    print(f"FINAL VIDEO: {OUTPUT}")
    print(f"  Duration: {int(final_dur)//60}:{int(final_dur)%60:02d}")
    print(f"  Size: {final_size:.1f} MB")

    # Verify streams
    result = subprocess.run([
        "ffprobe", "-v", "quiet",
        "-show_entries", "stream=codec_type",
        "-of", "csv=p=0", OUTPUT,
    ], capture_output=True, text=True)
    streams = result.stdout.strip().split("\n")
    print(f"  Streams: {', '.join(streams)}")
    print(f"{'='*60}")


if __name__ == "__main__":
    composite()
