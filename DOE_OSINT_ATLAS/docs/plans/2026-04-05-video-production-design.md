# Video Production Pipeline — Design

> Approved 2026-04-05

## Goal
Produce a polished 11-minute technical briefing video with Brian voiceover synced to choreographed UI demonstrations of each OSINT layer, with smooth visual transitions.

## Architecture
- Strip section headers from narration, regenerate audio in single ElevenLabs API call (no chunking)
- Single continuous Playwright recording with JS-injected transition effects (fade, title cards, highlight pulses, smooth scrolling)
- ffmpeg merge to final MP4

## Key Decisions
- Battelle Memorial Institute (index 11) for Section 1 pipeline walkthrough (11/14 layer coverage)
- Four Rivers Nuclear for Section 2 case study (per narration script)
- Single-take recording (no stitching) to avoid transition artifacts
- All visual effects injected via `page.evaluate()` — no frontend code changes
