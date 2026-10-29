# Viral Video Creator

A $0-first topic-to-video generator designed to run from GitHub Actions. It requests short, original text-to-video clips from the public LTX-Video hosted demo, then assembles them with narration, captions, and a thumbnail. It does not intentionally substitute abstract circles or stock footage when generation fails.

## Output

Every run creates a folder under `output/<run-id>/` containing:
- `final.mp4` — 1080×1920, **60 FPS**, H.264, ready for vertical short-form platforms.
- `thumbnail.jpg` — extracted from the finished video.
- `captions.srt` — subtitle file.
- `captions-hashtags.txt` — narration/caption copy and generated hashtags.
- `storyboard.json` and `manifest.json` — the scene plan and technical QC report.
- `scenes/` — individual 60 FPS scene renders.

## Visual approach

The visual engine requests genuine generated video clips from the public LTX-Video hosted demo, then uses FFmpeg to crop to 9:16 and master at 1080×1920 / 60 FPS. It uses no paid video API and does not download stock footage. The hosted GPU is shared and may be queued, paused, or rate-limited; failed generation stops the workflow instead of falling back to abstract motion graphics. If Gemini is unavailable, the storyboard attempts to use Wikipedia's free public API for factual context and fails clearly if it cannot obtain research.

## Run in GitHub

1. Open the **Actions** tab.
2. Select **Generate Viral Video**.
3. Click **Run workflow**.
4. Enter a topic and optional style notes.
5. Download the generated MP4, thumbnail and captions from the run's artifact.

The workflow uses Python, FFmpeg and Kokoro TTS. Gemini can provide stronger storyboards when `GEMINI_API_KEY` is available; without it, the script attempts free Wikipedia research rather than inventing a generic explanation. `HF_TOKEN` is optional and may help if the hosted demo requires authentication, but does not provide paid capacity.

## Local run

Requires Python 3.11+, FFmpeg, and the packages in `requirements.txt`.

```bash
pip install -r requirements.txt
python main.py --topic "Why phones are becoming insanely powerful"
```

## Notes

60 FPS increases render time and artifact size. The pipeline verifies the final frame rate with ffprobe and fails QC if the output is not 60 FPS. The generator creates an original visual treatment; it does not promise photorealistic text-to-video results.
