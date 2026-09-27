# Viral Video Creator

AI-first autonomous vertical video production.

## What it does

The system now runs in two modes:

- Manual: give it a topic.
- Autopilot: discover fresh short-form topics, choose one, generate multiple hooks, write the story, generate every scene with AI video, add voice/captions, run QC, and report the result to Discord.

Pipeline:

trend discovery -> topic selection -> hook variants -> AI creative director -> storyboard -> AI text-to-video scenes -> voiceover -> captions -> mastering -> QC -> Discord.

The primary renderer generates the visuals itself. It does not depend on random stock footage.

## Setup

Requires Python 3.11+ and FFmpeg.

    pip install -r requirements.txt

Set:

- FAL_KEY — required for AI video generation.
- GEMINI_API_KEY — recommended for stronger scripts/storyboards.
- YOUTUBE_API_KEY — optional for fresh YouTube Shorts trend discovery.
- DISCORD_WEBHOOK_URL — pipeline events.
- DISCORD_WEBHOOK_VIDEO_URL — final-video events.

### Manual

    python main.py --topic "Why phones are becoming insanely powerful"

### Autonomous

    python main.py --autopilot

If no YouTube API key is configured, the autopilot uses a small safe fallback topic pool rather than scraping arbitrary videos.

## GitHub Actions

The workflow supports:

- manual workflow_dispatch with an optional topic
- scheduled autonomous generation every 6 hours
- artifact upload of the complete run

Add the secrets above in the repository settings. YOUTUBE_API_KEY is optional; the other generation keys are used by the production pipeline.

## Output

Every run creates a timestamped directory containing:

- AI-generated scene MP4s
- trend.json when autopilot is used
- storyboard.json
- voice.mp3
- captions.srt
- final.mp4
- manifest.json

The manifest records the selected trend, hook variants, generation mode, scene metadata, and final QC.
