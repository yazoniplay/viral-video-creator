import subprocess
from pathlib import Path

FONT_BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REGULAR="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

def _escape_drawtext(text: str) -> str:
    return (str(text).replace("\\","\\\\").replace(":","\\:")
        .replace("'","\\'").replace("%","\\%").replace("[","\\[").replace("]","\\]").replace(",","\\,"))

def concat_scenes(scenes: list[Path], output: Path):
    listing=output.with_suffix(".txt")
    listing.write_text(
        "".join(f"file '{p.resolve()}'\n" for p in scenes),
        encoding="utf-8",
    )
    subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(listing),
        "-an","-vf","setpts=PTS-STARTPTS,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,format=yuv420p",
        "-r","30","-fps_mode","cfr","-c:v","libx264","-preset","medium","-crf","18",str(output)],check=True)

def add_voice(video: Path,voice: Path,output: Path):
    subprocess.run(["ffmpeg","-y","-i",str(video),"-i",str(voice),"-map","0:v:0","-map","1:a:0",
        "-c:v","copy","-c:a","aac","-b:a","192k","-shortest",str(output)],check=True)

def _drawtext(font: str, text: str, size: int, x: int, y: int, color: str,
              shadow: float = 0.8, shadow_x: int = 2, shadow_y: int = 2,
              enable: str | None = None) -> str:
    parts = [
        "drawtext", f"fontfile={font}", f"text='{_escape_drawtext(text)}'",
        f"fontcolor={color}", f"fontsize={size}", f"x={x}", f"y={y}",
        f"shadowcolor=black@{shadow}", f"shadowx={shadow_x}", f"shadowy={shadow_y}"
    ]
    if enable:
        parts.append(f"enable='{enable}'")
    return ":".join(parts)

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
    filters.append("drawbox=x=28:y=190:w=490:h=1120:color=black@0.48:t=fill")
    filters.append(_drawtext(FONT_BOLD, storyboard.get("title") or "TOP 5", 52, 62, 92, "white"))
    for pos,entry in enumerate(entries):
        rank=int(entry.get("rank",pos+1))
        name=_escape_drawtext(entry.get("name") or f"Rank {rank}")
        y=255+pos*205
        filters.append(_drawtext(FONT_BOLD, str(rank), 64, 62, y, "white"))
        filters.append(_drawtext(FONT_REGULAR, name, 31, 145, y+12, "white"))
        scene_index=max(0,5-rank)
        start=scene_index*per_scene
        end=min(total_duration,(scene_index+1)*per_scene)
        enable=f"between(t,{start:.3f},{end:.3f})"
        filters.append(_drawtext(FONT_BOLD, str(rank), 72, 58, y-4, "yellow", 0.9, 3, 3, enable))
        filters.append(_drawtext(FONT_BOLD, name, 34, 141, y+9, "yellow", 0.9, 3, 3, enable))
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
    raw=subprocess.check_output(["ffprobe","-v","error","-show_entries","stream=width,height,codec_name,duration",
        "-of","json",str(video)],text=True)
    v=next(s for s in json.loads(raw)["streams"] if s.get("width"))
    return {"width":v["width"],"height":v["height"],"codec":v["codec_name"],
            "duration":float(v.get("duration") or 0),"vertical":v["height"]>v["width"]}
