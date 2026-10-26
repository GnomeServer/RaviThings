#!/usr/bin/env python3
"""
Generate voiceover audio using Gemini TTS.

Advantages over ElevenLabs:
- 32K token context — no chunking needed for our 10,922 char narration
- Persona prompting for voice character control
- No per-character billing

Usage:
  python3 generate_gemini_tts.py
"""

import os
import wave
import struct
from dotenv import load_dotenv

load_dotenv()

from google import genai
from google.genai import types

AUDIO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "videos", "audio")
NARRATION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "videos", "combined_narration_tts.txt")


def generate_tts():
    """Generate the full briefing audio in a single Gemini TTS call."""
    os.makedirs(AUDIO_DIR, exist_ok=True)

    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

    # Read the narration
    with open(NARRATION_FILE) as f:
        narration = f.read()

    print(f"Narration: {len(narration)} chars")

    # Build the TTS prompt with persona direction
    prompt = f"""<PERSONA>
You are a senior intelligence analyst delivering a classified briefing to
a room of DOE and NSA officers. Your voice is deep, measured, and authoritative —
like Edward R. Murrow narrating a documentary about something that should
alarm everyone in the room. You speak with the weight of someone who has
verified every fact personally. You don't rush. You let the findings land.

When you reach statistics, slow slightly — let each number register.
When you reach "A fourteen-year-old SSH implementation on a three-billion-dollar
research contractor" — let the absurdity of that sentence do the work.
When you reach "The supply chain is the perimeter" — this is the thesis.
Deliver it with finality.
</PERSONA>

<NARRATION>
{narration}
</NARRATION>"""

    print("Generating TTS with Gemini...")
    print(f"  Model: gemini-2.5-flash-preview-tts")
    print(f"  Voice: Enceladus (deep, breathy)")

    response = client.models.generate_content(
        model="gemini-2.5-flash-preview-tts",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Enceladus"
                    )
                )
            ),
        ),
    )

    # Extract audio data
    audio_data = response.candidates[0].content.parts[0].inline_data.data
    print(f"  Raw audio: {len(audio_data)} bytes")

    # Save as WAV (PCM 24000 Hz)
    wav_path = os.path.join(AUDIO_DIR, "osint_atlas_briefing_gemini.wav")
    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(24000)
        wf.writeframes(audio_data)

    wav_size = os.path.getsize(wav_path)
    print(f"  WAV saved: {wav_path} ({wav_size / 1024 / 1024:.1f} MB)")

    # Convert to MP3 for consistency with existing pipeline
    mp3_path = os.path.join(AUDIO_DIR, "osint_atlas_briefing_gemini.mp3")
    import subprocess
    result = subprocess.run([
        "ffmpeg", "-y",
        "-i", wav_path,
        "-codec:a", "libmp3lame",
        "-b:a", "128k",
        mp3_path,
    ], capture_output=True, text=True)

    if result.returncode == 0:
        mp3_size = os.path.getsize(mp3_path)
        # Get duration
        dur_result = subprocess.run([
            "ffprobe", "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "csv=p=0", mp3_path,
        ], capture_output=True, text=True)
        duration = float(dur_result.stdout.strip())
        print(f"  MP3 saved: {mp3_path} ({mp3_size / 1024 / 1024:.1f} MB, {int(duration)//60}:{int(duration)%60:02d})")
    else:
        print(f"  ffmpeg error: {result.stderr[:200]}")

    return mp3_path


if __name__ == "__main__":
    generate_tts()
