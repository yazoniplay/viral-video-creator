from pathlib import Path
import os
import urllib.request
import fal_client
from config import FAL_KEY, VIDEO_MODEL, VIDEO_RESOLUTION, VIDEO_ASPECT_RATIO, VIDEO_SCENE_SECONDS

def generate_scene(prompt: str, output_path: Path) -> dict:
    if not FAL_KEY:
        raise RuntimeError("FAL_KEY is missing.")
    os.environ["FAL_KEY"] = FAL_KEY
    result = fal_client.subscribe(
        VIDEO_MODEL,
        arguments={
            "prompt": prompt,
            "resolution": VIDEO_RESOLUTION,
            "aspect_ratio": VIDEO_ASPECT_RATIO,
            "duration": VIDEO_SCENE_SECONDS,
            "prompt_expansion_mode": "balanced",
        },
        with_logs=False,
    )
    video = result.get("video") if isinstance(result, dict) else None
    url = video.get("url") if isinstance(video, dict) else None
    if not url:
        raise RuntimeError(f"Video provider returned no video URL: {result}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, output_path)
    return {"url": url, "model": VIDEO_MODEL, "path": str(output_path)}
