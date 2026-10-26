#!/usr/bin/env python3
"""
Generate Gemini TTS audio for each act separately.

Produces 7 individual audio files, one per act. These get placed at
specific video timestamps during compositing, with silence in between
if needed. This approach solves the timing problem: the video is the
master clock, not the audio.

Usage:
  python3 generate_act_audio.py [--act 1-7|all]
"""

import argparse
import os
import subprocess
import wave

from dotenv import load_dotenv

load_dotenv()

from google import genai
from google.genai import types

AUDIO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "videos", "audio", "acts")
NARRATION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "videos", "combined_narration_tts.txt")

# Persona prompt for consistent voice across all chunks
PERSONA = """You are a senior intelligence analyst delivering a briefing.
Your voice is deep, measured, and authoritative. You speak with the weight
of someone who has verified every fact personally. You don't rush.
When you reach statistics, slow slightly — let each number register.
Deliver findings with gravity but without melodrama."""


def split_narration():
    """Split the narration into 7 acts based on content boundaries."""
    text = open(NARRATION_FILE).read()

    boundaries = [
        text.find("This is Four Rivers Nuclear"),
        text.find("Now \u2014 from those observed services"),
        text.find("Now. A significant finding."),
        text.find("Let me put the full picture"),
        text.find("So \u2014 how did we get all of this"),
        text.find("The data shows something"),
    ]

    acts = []
    starts = [0] + boundaries
    ends = boundaries + [len(text)]

    act_names = [
        "act1_hook",
        "act2_findings",
        "act3_attack",
        "act4_dmarc",
        "act5_surface",
        "act6_pipeline",
        "act7_conclusion",
    ]

    for i, name in enumerate(act_names):
        chunk = text[starts[i]:ends[i]].strip()
        acts.append({"name": name, "text": chunk})

    return acts


def generate_act_audio(client, act, voice="Enceladus"):
    """Generate TTS audio for a single act."""
    name = act["name"]
    text = act["text"]

    print(f"\n  Generating: {name} ({len(text)} chars)")

    prompt = f"{PERSONA}\n\n{text}"

    response = client.models.generate_content(
        model="gemini-2.5-flash-preview-tts",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice
                    )
                )
            ),
        ),
    )

    audio_data = response.candidates[0].content.parts[0].inline_data.data

    # Save as WAV
    wav_path = os.path.join(AUDIO_DIR, f"{name}.wav")
    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(audio_data)

    # Convert to MP3
    mp3_path = os.path.join(AUDIO_DIR, f"{name}.mp3")
    subprocess.run([
        "ffmpeg", "-y", "-i", wav_path,
        "-codec:a", "libmp3lame", "-b:a", "128k",
        mp3_path,
    ], capture_output=True)

    # Get duration
    result = subprocess.run([
        "ffprobe", "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "csv=p=0", mp3_path,
    ], capture_output=True, text=True)
    duration = float(result.stdout.strip())

    size = os.path.getsize(mp3_path)
    print(f"    Saved: {mp3_path} ({size / 1024:.0f} KB, {int(duration)//60}:{int(duration)%60:02d})")

    # Clean up WAV
    os.unlink(wav_path)

    return {"name": name, "path": mp3_path, "duration": duration}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--act", default="all", help="Which act: 1-7 or all")
    parser.add_argument("--voice", default="Enceladus", help="Gemini voice name")
    args = parser.parse_args()

    os.makedirs(AUDIO_DIR, exist_ok=True)

    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    acts = split_narration()

    if args.act == "all":
        to_generate = acts
    else:
        idx = int(args.act) - 1
        to_generate = [acts[idx]]

    print("=" * 60)
    print("Generating per-act Gemini TTS audio")
    print("=" * 60)

    results = []
    for act in to_generate:
        result = generate_act_audio(client, act, voice=args.voice)
        results.append(result)

    print(f"\n{'='*60}")
    print("RESULTS:")
    total_duration = 0
    for r in results:
        print(f"  {r['name']}: {r['duration']:.1f}s ({int(r['duration'])//60}:{int(r['duration'])%60:02d})")
        total_duration += r["duration"]
    print(f"\n  Total audio: {total_duration:.1f}s ({int(total_duration)//60}:{int(total_duration)%60:02d})")

    # Save a manifest for the compositing script
    manifest_path = os.path.join(AUDIO_DIR, "manifest.txt")
    with open(manifest_path, "w") as f:
        for r in results:
            f.write(f"{r['name']}\t{r['duration']:.3f}\t{r['path']}\n")
    print(f"\n  Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
