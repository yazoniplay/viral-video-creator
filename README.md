# Viral Video Creator

AI-first automated vertical video production.

Pipeline:
topic -> AI creative director -> storyboard -> **AI text-to-video scenes** -> voiceover -> captions -> mastering -> QC -> Discord.

The primary renderer generates the visuals itself. It does not scrape random web videos.

## Setup

Requires Python 3.11+ and FFmpeg.

    pip install -r requirements.txt
    python main.py --topic "Why phones are becoming insanely powerful"

Set FAL_KEY. Optional GEMINI_API_KEY upgrades the fallback storyboard into an AI creative director.

The default provider is MiniMax H3 Max through fal.ai. The provider is isolated in ai_video.py so another model can be added later.

## Discord

Use DISCORD_WEBHOOK_URL for pipeline events and DISCORD_WEBHOOK_VIDEO_URL for final-video events.

## Output

Every run creates AI-generated scene MP4s, storyboard.json, voice.mp3, captions.srt, final.mp4 and manifest.json.
