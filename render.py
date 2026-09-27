import subprocess
from pathlib import Path

def concat_scenes(scenes: list[Path], output: Path):
    listing=output.with_suffix(".txt")
    listing.write_text("".join(f"file '{p.resolve()}'\n" for p in scenes),encoding="utf-8")
    subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(listing),
        "-an","-vf","scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,format=yuv420p",
        "-c:v","libx264","-preset","medium","-crf","18",str(output)],check=True)

def add_voice(video: Path,voice: Path,output: Path):
    subprocess.run(["ffmpeg","-y","-i",str(video),"-i",str(voice),"-map","0:v:0","-map","1:a:0",
        "-c:v","copy","-c:a","aac","-b:a","192k","-shortest",str(output)],check=True)

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
