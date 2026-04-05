#!/usr/bin/env python3
"""
Composite per-act audio onto the screen recording.

Reads transition_timestamps.txt (written by record_combined.py) to know
exactly when each act begins in the video. Places each act's audio chunk
at that timestamp. Silence fills any gaps between acts.

Usage:
  1. Run record_combined.py first (generates video + transition timestamps)
  2. Run generate_act_audio.py (generates per-act audio)
  3. Run this script to composite

Output: videos/osint_atlas_final_composite.mp4
"""

import os
import subprocess
import sys

VIDEO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "videos")
ACTS_DIR = os.path.join(VIDEO_DIR, "audio", "acts")
CLIPS_DIR = os.path.join(VIDEO_DIR, "veo_clips")

# Input files
SCREEN_RECORDING = os.path.join(VIDEO_DIR, "osint_atlas_briefing.webm")
TRANSITION_LOG = os.path.join(VIDEO_DIR, "transition_timestamps.txt")
VEO_OPENING = os.path.join(CLIPS_DIR, "opening.mp4")
VEO_CLOSING = os.path.join(CLIPS_DIR, "closing.mp4")

# Output
OUTPUT = os.path.join(VIDEO_DIR, "osint_atlas_final_composite.mp4")


def get_duration(path):
    result = subprocess.run([
        "ffprobe", "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "csv=p=0", path,
    ], capture_output=True, text=True)
    return float(result.stdout.strip())


def read_transitions():
    """Read transition timestamps from the recording."""
    transitions = {}
    with open(TRANSITION_LOG) as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) == 2:
                transitions[parts[1]] = float(parts[0])
    return transitions


def main():
    print("=" * 60)
    print("Compositing per-act audio onto video")
    print("=" * 60)

    # Check inputs
    for name, path in [("Screen recording", SCREEN_RECORDING),
                        ("Transition log", TRANSITION_LOG)]:
        if not os.path.exists(path):
            print(f"MISSING: {name} — {path}")
            sys.exit(1)

    # Read transition timestamps
    transitions = read_transitions()
    print(f"\nTransition timestamps (from video recording):")
    for act, ts in sorted(transitions.items(), key=lambda x: x[1]):
        print(f"  {act}: {int(ts)//60}:{int(ts)%60:02d} ({ts:.1f}s)")

    # Check act audio files
    act_names = ["act1_hook", "act2_findings", "act3_attack", "act4_dmarc",
                 "act5_surface", "act6_pipeline", "act7_conclusion"]
    act_audio = {}
    for name in act_names:
        path = os.path.join(ACTS_DIR, f"{name}.mp3")
        if os.path.exists(path):
            dur = get_duration(path)
            act_audio[name] = {"path": path, "duration": dur}
            print(f"  {name}: {dur:.1f}s audio")
        else:
            print(f"  MISSING: {path}")

    # Get video duration
    veo_opening_dur = get_duration(VEO_OPENING) if os.path.exists(VEO_OPENING) else 0
    recording_dur = get_duration(SCREEN_RECORDING)
    veo_closing_dur = get_duration(VEO_CLOSING) if os.path.exists(VEO_CLOSING) else 0

    print(f"\nVideo segments:")
    print(f"  Veo opening: {veo_opening_dur:.1f}s")
    print(f"  Recording: {recording_dur:.1f}s")
    print(f"  Veo closing: {veo_closing_dur:.1f}s")

    # Step 1: Build the video track (opening + recording + closing)
    print("\nStep 1: Building video track...")

    # Scale Veo clips
    scaled = {}
    for name, src in [("opening", VEO_OPENING), ("closing", VEO_CLOSING)]:
        if os.path.exists(src):
            dst = os.path.join(CLIPS_DIR, f"{name}_1080.mp4")
            subprocess.run([
                "ffmpeg", "-y", "-i", src,
                "-vf", "scale=1920:1080:flags=lanczos,setsar=1",
                "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-an",
                dst,
            ], capture_output=True)
            scaled[name] = dst

    # Convert recording to h264
    recording_h264 = os.path.join(VIDEO_DIR, "recording_h264.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-i", SCREEN_RECORDING,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-an",
        recording_h264,
    ], capture_output=True)

    # Concatenate video segments
    concat_list = os.path.join(VIDEO_DIR, "concat_list.txt")
    with open(concat_list, "w") as f:
        if "opening" in scaled:
            f.write(f"file '{scaled['opening']}'\n")
        f.write(f"file '{recording_h264}'\n")
        if "closing" in scaled:
            f.write(f"file '{scaled['closing']}'\n")

    video_only = os.path.join(VIDEO_DIR, "video_no_audio.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        video_only,
    ], capture_output=True)

    video_total_dur = get_duration(video_only)
    print(f"  Video track: {video_total_dur:.1f}s")

    # Step 2: Build the audio track
    # Each act audio starts at: veo_opening_dur + transition_timestamp
    print("\nStep 2: Building audio track with per-act placement...")

    # Generate a silence base track matching video duration
    silence_path = os.path.join(VIDEO_DIR, "silence.mp3")
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=mono",
        "-t", str(video_total_dur),
        "-codec:a", "libmp3lame", "-b:a", "128k",
        silence_path,
    ], capture_output=True)

    # Build ffmpeg filter to overlay each act audio at its timestamp
    inputs = ["-i", silence_path]  # Input 0: silence base
    filter_parts = []

    for i, name in enumerate(act_names):
        if name not in act_audio or name not in transitions:
            continue

        audio_info = act_audio[name]
        # Offset = veo opening + transition timestamp in recording
        offset = veo_opening_dur + transitions[name]
        inputs.extend(["-i", audio_info["path"]])
        input_idx = i + 1  # 0 is silence

        # Delay this audio to the right position
        filter_parts.append(
            f"[{input_idx}]adelay={int(offset * 1000)}|{int(offset * 1000)}[a{i}]"
        )

    # Mix all delayed audio tracks together
    if filter_parts:
        mix_inputs = "[0]" + "".join(f"[a{i}]" for i in range(len(filter_parts)))
        n_inputs = len(filter_parts) + 1
        filter_str = ";".join(filter_parts) + f";{mix_inputs}amix=inputs={n_inputs}:duration=first[out]"

        print(f"  Mixing {len(filter_parts)} audio acts...")
        audio_mixed = os.path.join(VIDEO_DIR, "audio_mixed.mp3")
        cmd = [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", filter_str,
            "-map", "[out]",
            "-codec:a", "libmp3lame", "-b:a", "128k",
            audio_mixed,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  Audio mix error: {result.stderr[:500]}")
            return
    else:
        print("  No audio acts to mix!")
        return

    audio_dur = get_duration(audio_mixed)
    print(f"  Mixed audio: {audio_dur:.1f}s")

    # Step 3: Combine video + mixed audio
    print("\nStep 3: Final composite...")
    result = subprocess.run([
        "ffmpeg", "-y",
        "-i", video_only,
        "-i", audio_mixed,
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        OUTPUT,
    ], capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  ERROR: {result.stderr[:300]}")
        return

    final_dur = get_duration(OUTPUT)
    final_size = os.path.getsize(OUTPUT) / 1024 / 1024

    print(f"\n{'='*60}")
    print(f"FINAL VIDEO: {OUTPUT}")
    print(f"  Duration: {int(final_dur)//60}:{int(final_dur)%60:02d}")
    print(f"  Size: {final_size:.1f} MB")

    # Show the audio placement for verification
    print(f"\nAudio placement (in composite video):")
    for name in act_names:
        if name in transitions and name in act_audio:
            offset = veo_opening_dur + transitions[name]
            dur = act_audio[name]["duration"]
            end = offset + dur
            print(f"  {name}: {int(offset)//60}:{int(offset)%60:02d} → "
                  f"{int(end)//60}:{int(end)%60:02d} ({dur:.0f}s)")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
