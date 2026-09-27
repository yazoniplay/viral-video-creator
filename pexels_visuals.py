import re
import subprocess
from pathlib import Path
import requests

from config import PEXELS_API_KEY, VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_SCENE_SECONDS

API = "https://api.pexels.com/v1/videos/search"

def _query(topic: str, scene: dict) -> str:
    prompt = str(scene.get("prompt", ""))
    # Prefer concrete visual nouns over the full creative prompt.
    words = re.findall(r"[A-Za-z0-9]+", prompt.lower())
    stop = {"vertical","cinematic","scene","visualize","visual","realistic","motion","dynamic","premium","lighting","style","about","show","with","the","and","for","from","this","that","no","logos","text"}
    useful = [w for w in words if w not in stop and len(w) > 2]
    base = " ".join(useful[:7])
    return base or topic

def _download(url: str, path: Path):
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with path.open("wb") as f:
            for chunk in r.iter_content(1024 * 1024):
                if chunk:
                    f.write(chunk)

def make_scene(topic: str, scene: dict, index: int, output: Path) -> dict:
    if not PEXELS_API_KEY:
        raise RuntimeError("PEXELS_API_KEY is missing. Add your Pexels API key to GitHub Actions secrets.")

    query = _query(topic, scene)
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": query, "orientation": "portrait", "size": "medium", "per_page": 15}
    r = requests.get(API, headers=headers, params=params, timeout=30)
    r.raise_for_status()
    videos = r.json().get("videos", [])
    if not videos:
        # Broaden the search before failing.
        params["query"] = topic
        r = requests.get(API, headers=headers, params=params, timeout=30)
        r.raise_for_status()
        videos = r.json().get("videos", [])
    if not videos:
        raise RuntimeError(f"No Pexels video found for query: {query}")

    # Pick a different result for each scene where possible.
    video = videos[(index - 1) % len(videos)]
    files = [x for x in video.get("video_files", []) if x.get("file_type") == "video/mp4" and x.get("link")]
    files.sort(key=lambda x: (abs((x.get("height", 0) / max(x.get("width", 1), 1)) - 16/9), -(x.get("width", 0))))
    if not files:
        raise RuntimeError(f"Pexels returned no downloadable MP4 for video {video.get('id')}")

    source = output.with_suffix(".source.mp4")
    _download(files[0]["link"], source)

    output.parent.mkdir(parents=True, exist_ok=True)
    duration = VIDEO_SCENE_SECONDS
    vf = (
        f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},"
        "setsar=1,"
        "eq=saturation=1.08:contrast=1.03,"
        "drawtext=text='Footage: Pexels':"
        "x=w-tw-45:y=h-th-45:fontsize=28:fontcolor=white@0.82:"
        "box=1:boxcolor=black@0.35:boxborderw=10"
    )
    subprocess.run([
        "ffmpeg","-y","-stream_loop","-1","-i",str(source),
        "-t",str(duration),"-vf",vf,
        "-an","-c:v","libx264","-preset","veryfast","-crf","21",
        "-pix_fmt","yuv420p","-movflags","+faststart",str(output)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    source.unlink(missing_ok=True)

    return {
        "path": str(output),
        "renderer": "pexels_stock_video",
        "index": index,
        "pexels_video_id": video.get("id"),
        "pexels_url": video.get("url"),
        "search_query": query,
        "credit": "Footage provided by Pexels"
    }
