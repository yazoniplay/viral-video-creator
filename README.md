# Viral Video Creator

A $0-first, topic-to-video generator designed to run entirely from GitHub Actions. It creates original animated footage locally, writes narration and captions, assembles a finished MP4, and exports a thumbnail plus a captions/hashtags file.

## Output

Every run creates a folder under `output/<run-id>/` containing:
- `final.mp4` — 1080×1920, **60 FPS**, H.264, ready for vertical short-form platforms.
- `thumbnail.jpg` — extracted from the finished video.
- `captions.srt` — subtitle file.
- `captions-hashtags.txt` — narration/caption copy and generated hashtags.
- `storyboard.json` and `manifest.json` — the scene plan and technical QC report.
- `scenes/` — individual 60 FPS scene renders.

## Visual approach

The visual engine renders original motion graphics from code: animated light fields, parallax particles, perspective grids, orbital geometry, moving beams, scene-specific compositions, controlled push-ins, and editorial typography. It does **not** download stock footage or call a paid video-generation API. This is stylized procedural footage rather than photorealistic AI video.

## Run in GitHub

1. Open the **Actions** tab.
2. Select **Generate Viral Video**.
3. Click **Run workflow**.
4. Enter a topic and optional style notes.
5. Download the generated MP4, thumbnail and captions from the run's artifact.

The workflow uses Python, FFmpeg, Pillow, NumPy and local Kokoro TTS. Gemini is optional for stronger scripts/storyboards; when configured, add `GEMINI_API_KEY` in repository Actions secrets. Without it, the local fallback still works. No Pexels key is required for the procedural footage engine.

## Local run

Requires Python 3.11+, FFmpeg, and the packages in `requirements.txt`.

```bash
pip install -r requirements.txt
python main.py --topic "Why phones are becoming insanely powerful"
```

## Notes

60 FPS increases render time and artifact size. The pipeline verifies the final frame rate with ffprobe and fails QC if the output is not 60 FPS. The generator creates an original visual treatment; it does not promise photorealistic text-to-video results.
