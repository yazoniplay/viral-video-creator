"""Generate real footage with the public LTX-Video ZeroGPU Space.

No paid API is used. The hosted demo has shared, limited free GPU capacity, so
requests may queue or fail. We deliberately fail instead of silently replacing
failed footage with animated circles or abstract graphics.
"""
from __future__ import annotations

import json
import os
import time
import urllib.parse
from pathlib import Path

import requests

SPACE_BASE_URL = "https://lightricks-ltx-video-distilled.hf.space"
API_NAME = "text_to_video"
NEGATIVE_PROMPT = (
    "abstract shapes, floating circles, geometric motion graphics, text, subtitles, "
    "watermarks, logos, blurry, distorted anatomy, flicker, low quality, still image"
)


def _headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    token = os.getenv("HF_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _parse_completed_event(raw: str):
    for block in reversed([part for part in raw.split("\n\n") if part.strip()]):
        event = None
        data = None
        for line in block.splitlines():
            if line.startswith("event:"):
                event = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data = line.split(":", 1)[1].strip()
        if event == "error":
            # Gradio sometimes reports a ZeroGPU/model crash as the literal JSON null.
            # Preserve the response context so the next failure is diagnosable.
            raise RuntimeError(f"LTX-Video generation failed: {data or 'unknown model error'}")
        if event == "complete" and data:
            payload = json.loads(data)
            video_field = payload[0] if isinstance(payload, list) and payload else None
            if isinstance(video_field, dict):
                video = video_field.get("video", video_field)
                if isinstance(video, dict):
                    url = video.get("url") or video.get("path")
                    if url:
                        return urllib.parse.urljoin(SPACE_BASE_URL + "/", str(url))
            raise RuntimeError(f"LTX-Video returned an unexpected result: {str(payload)[:400]}")
    raise RuntimeError("LTX-Video closed the queue stream without returning a video.")


def _generate_remote(prompt: str, duration: float, scene: dict | None = None) -> str:
    # Keep each generation small enough for a shared free ZeroGPU queue.
    seconds = max(2.0, min(5.0, float(duration)))
    # Vertical aspect ratio, within the public Space's advertised limits.
    landscape = bool((scene or {}).get("aspect") == "landscape")
    height, width = (512, 896) if landscape else (896, 512)
    data = [
        prompt,
        NEGATIVE_PROMPT,
        "",
        "",
        height,
        width,
        "text-to-video",
        seconds,
        9,
        0,
        True,
        1,
        False,
    ]
    headers = _headers()
    last_error = None
    # The public ZeroGPU Space can occasionally fail a generation with an empty
    # Gradio error payload. Retry twice with the slower multi-pass texture stage
    # disabled above, then fail with the actual error instead of fake footage.
    for attempt in range(1, 4):
        try:
            submit = requests.post(
                f"{SPACE_BASE_URL}/gradio_api/call/{API_NAME}",
                headers=headers,
                json={"data": data},
                timeout=45,
            )
            if not submit.ok:
                raise RuntimeError(
                    f"Free LTX-Video service rejected the request (HTTP {submit.status_code}). "
                    "Its shared GPU may be busy, paused, or out of quota."
                )
            event_id = submit.json().get("event_id")
            if not event_id:
                raise RuntimeError("Free LTX-Video service did not return a queue ID.")

            print(f"[video] queued real text-to-video generation (attempt {attempt}/3); waiting for shared GPU...", flush=True)
            result = requests.get(
                f"{SPACE_BASE_URL}/gradio_api/call/{API_NAME}/{event_id}",
                headers=headers,
                timeout=(20, 360),
            )
            if not result.ok:
                raise RuntimeError(f"Lost connection to LTX-Video (HTTP {result.status_code}).")
            return _parse_completed_event(result.text)
        except requests.RequestException as exc:
            last_error = RuntimeError(
                "Could not reach the free LTX-Video service. The shared demo may be asleep, "
                "rate-limited, or unavailable."
            )
            last_error.__cause__ = exc
        except RuntimeError as exc:
            last_error = exc

        if attempt < 3:
            print(f"[video] generation attempt {attempt} failed: {last_error}; retrying in 8 seconds...", flush=True)
            time.sleep(8)

    raise RuntimeError(
        f"Free LTX-Video generation failed after 3 attempts: {last_error}. "
        "The shared hosted GPU may be overloaded or the model may have crashed. "
        "No synthetic-circle fallback was rendered."
    ) from last_error


def generate_scene(
    prompt: str,
    output_path: Path,
    topic: str = "",
    scene: dict | None = None,
    index: int = 1,
    duration: float | None = None,
) -> dict:
    scene = scene or {"purpose": "visual", "prompt": prompt}
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    scene_prompt = str(scene.get("prompt") or prompt or topic).strip()
    purpose = str(scene.get("purpose") or f"scene {index}")
    landscape = bool(scene.get("aspect") == "landscape")
    aspect_description = "landscape 16:9" if landscape else "vertical 9:16"
    # Ask for a concrete physical subject/action, not abstract design language.
    full_prompt = (
        f"Photorealistic cinematic documentary video, {aspect_description}. Subject/topic: {topic}. "
        f"Specific shot: {purpose}. Show this concrete visible action: {scene_prompt}. "
        "Real camera footage, natural physical movement, believable lighting, detailed environment, "
        "camera motion appropriate to the action. No text, no diagrams, no logos, no abstract shapes."
    )
    print(f"[video] generating real footage for scene {index}: {purpose}", flush=True)
    remote_url = _generate_remote(full_prompt, duration or 4.0, scene=scene)
    downloaded = output_path.with_suffix(".source.mp4")
    try:
        with requests.get(remote_url, headers=_headers(), stream=True, timeout=(20, 180)) as response:
            response.raise_for_status()
            with downloaded.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)
        if not downloaded.exists() or downloaded.stat().st_size < 20_000:
            raise RuntimeError("The hosted model returned an empty or invalid video file.")

        import subprocess
        target_duration = max(2.0, float(duration or 4.0))
        out_width, out_height = (1920, 1080) if landscape else (1080, 1920)
        command = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(downloaded),
            "-t", str(target_duration),
            "-vf",
            f"scale={out_width}:{out_height}:force_original_aspect_ratio=increase,"
            f"crop={out_width}:{out_height},fps=60,setsar=1",
            "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            str(output_path),
        ]
        subprocess.run(command, check=True, timeout=240)
        if not output_path.exists() or output_path.stat().st_size < 20_000:
            raise RuntimeError("FFmpeg produced no usable scene file.")
        return {
            "visual_engine": "LTX-Video hosted open model",
            "footage_generated": True,
            "source_url": remote_url,
            "source_duration_seconds": target_duration,
            "fps": 60,
            "width": out_width,
            "height": out_height,
        }
    finally:
        try:
            downloaded.unlink(missing_ok=True)
        except OSError:
            pass
