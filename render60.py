"""60 fps vertical assembly and delivery helpers."""
import json, subprocess
from pathlib import Path

FPS=60

def concat_scenes(scenes, output:Path, width=1080, height=1920):
    if not scenes: raise RuntimeError("No scenes to concatenate.")
    output.parent.mkdir(parents=True,exist_ok=True)
    args=["ffmpeg","-hide_banner","-loglevel","error","-y"]
    filters=[]
    for i,path in enumerate(scenes):
        args += ["-i",str(path)]
        filters.append(f"[{i}:v:0]setpts=PTS-STARTPTS,scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},setsar=1,fps={FPS},format=yuv420p[v{i}]")
    labels="".join(f"[v{i}]" for i in range(len(scenes)))
    filters.append(f"{labels}concat=n={len(scenes)}:v=1:a=0,setpts=PTS-STARTPTS[v]")
    args += ["-filter_complex",";".join(filters),"-map","[v]","-an","-r",str(FPS),"-fps_mode","cfr","-c:v","libx264","-preset","medium","-crf","18","-threads","2","-pix_fmt","yuv420p","-movflags","+faststart",str(output)]
    subprocess.run(args,check=True)
    return output

def add_voice(video:Path,voice:Path,output:Path,duration=None):
    args=["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(video),"-i",str(voice),"-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac","-b:a","160k","-af","apad","-r",str(FPS),"-fps_mode","cfr"]
    if duration is not None: args += ["-t",str(duration)]
    else: args += ["-shortest"]
    args += ["-movflags","+faststart",str(output)]
    subprocess.run(args,check=True)

def final_master(video:Path,output:Path):
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(video),
        "-vf",f"fps={FPS},eq=contrast=1.055:saturation=1.10:brightness=0.004,unsharp=5:5:0.35",
        "-c:v","libx264","-preset","veryfast","-crf","18","-threads","2","-pix_fmt","yuv420p",
        "-r",str(FPS),"-fps_mode","cfr","-c:a","aac","-b:a","160k","-movflags","+faststart",str(output)],check=True)

def validate(video:Path)->dict:
    raw=subprocess.check_output(["ffprobe","-v","error","-show_entries","stream=width,height,codec_name,duration,avg_frame_rate,r_frame_rate","-show_entries","format=duration","-of","json",str(video)],text=True)
    data=json.loads(raw); v=next(s for s in data["streams"] if s.get("width"))
    rate=v.get("avg_frame_rate","0/1")
    num,den=rate.split("/")
    fps=float(num)/max(float(den),1)
    result={"width":v["width"],"height":v["height"],"codec":v["codec_name"],"duration":float(data.get("format",{}).get("duration") or v.get("duration") or 0),"fps":fps,"vertical":v["height"]>v["width"]}
    if round(fps)!=FPS: raise RuntimeError(f"Final video is {fps:.3f} fps; expected {FPS}.")
    return result
