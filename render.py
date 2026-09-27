import re
import subprocess
from pathlib import Path

FONT_BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REGULAR="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

def _escape_drawtext(text: str) -> str:
    return (str(text).replace("\\","\\\\").replace(":","\\:")
        .replace("'","\\'").replace("%","\\%").replace("[","\\[").replace("]","\\]"))

def concat_scenes(scenes: list[Path], output: Path):
    listing=output.with_suffix(".txt")
    listing.write_text("".join(f"file '{p.resolve()}'\\n" for p in scenes),encoding="utf-8")
    subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(listing),
        "-an","-vf","scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,format=yuv420p",
        "-c:v","libx264","-preset","medium","-crf","18",str(output)],check=True)

def add_voice(video: Path,voice: Path,output: Path):
    subprocess.run(["ffmpeg","-y","-i",str(video),"-i",str(voice),"-map","0:v:0","-map","1:a:0",
        "-c:v","copy","-c:a","aac","-b:a","192k","-shortest",str(output)],check=True)

def apply_ranking_overlay(video: Path, storyboard: dict, output: Path, total_duration: float):
    entries=storyboard.get("ranking_entries") or []
    if not entries:
        entries=[]
        for i,scene in enumerate(storyboard.get("scenes",[]),1):
            entries.append({"rank":i,"name":scene.get("name") or scene.get("purpose") or f"Entry {i}"})
    entries=sorted(entries, key=lambda x:int(x.get("rank",0)))[:5]
    if not entries:
        video.replace(output)
        return

    scenes=storyboard.get("scenes",[])
    per_scene=total_duration/max(len(scenes),1)
    filters=[]
    # Soft panel keeps the leaderboard readable without covering the whole video.
    filters.append("drawbox=x=28:y=190:w=490:h=1120:color=black@0.48:t=fill")
    title=_escape_drawtext(storyboard.get("title") or "TOP 5")
    filters.append(
        f"drawtext=fontfile={FONT_BOLD}:text='{title}':fontcolor=white:fontsize=52:"
        "x=62:y=92:shadowcolor=black@0.8:shadowx=2:shadowy=2"
    )
    for pos,entry in enumerate(entries):
        rank=int(entry.get("rank",pos+1))
        name=_escape_drawtext(entry.get("name") or f"Rank {rank}")
        y=255+pos*205
        # Every rank remains visible. The active rank is drawn again in a brighter accent.
        filters.append(
            f"drawtext=fontfile={FONT_BOLD}:text='{rank}':fontcolor=white:fontsize=64:"
            f"x=62:y={y}:shadowcolor=black@0.8:shadowx=2:shadowy=2"
        )
        filters.append(
            f"drawtext=fontfile={FONT_REGULAR}:text='{name}':fontcolor=white:fontsize=31:"
            f"x=145:y={y+12}:shadowcolor=black@0.8:shadowx=2:shadowy=2"
        )
        scene_index=max(0,5-rank)
        start=scene_index*per_scene
        end=min(total_duration,(scene_index+1)*per_scene)
        filters.append(
            f"drawtext=fontfile={FONT_BOLD}:text='{rank}':fontcolor=yellow:fontsize=72:"
            f"x=58:y={y-4}:shadowcolor=black@0.9:shadowx=3:shadowy=3:"
            f"enable='between(t,{start:.3f},{end:.3f})'"
        )
        filters.append(
            f"drawtext=fontfile={FONT_BOLD}:text='{name}':fontcolor=yellow:fontsize=34:"
            f"x=141:y={y+9}:shadowcolor=black@0.9:shadowx=3:shadowy=3:"
            f"enable='between(t,{start:.3f},{end:.3f})'"
        )
    vf=",".join(filters)
    subprocess.run(["ffmpeg","-y","-i",str(video),"-vf",vf,"-c:v","libx264","-preset","medium",
        "-crf","18","-pix_fmt","yuv420p","-an",str(output)],check=True)

def final_master(video: Path,output: Path):
    subprocess.run(["ffmpeg","-y","-i",str(video),
        "-vf","eq=contrast=1.04:saturation=1.06:brightness=0.01,unsharp=5:5:0.35",
        "-c:v","libx264","-preset","medium","-crf","17","-c:a","aac","-b:a","192k",
        "-movflags","+faststart",str(output)],check=True)

def validate(video: Path)->dict:
    import json
    raw=subprocess.check_output(["ffprobe","-v","error","-show_entries","stream=width,height,codec_name",
        "-of","json",str(video)],text=True)
    v=next(s for s in json.loads(raw)["streams"] if s.get("width"))
    return {"width":v["width"],"height":v["height"],"codec":v["codec_name"],"vertical":v["height"]>v["width"]}
