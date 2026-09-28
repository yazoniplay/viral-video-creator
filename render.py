import subprocess
from pathlib import Path

FONT_BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REGULAR="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def _ass_escape(text: str) -> str:
    return (
        str(text)
        .replace("\\", "\\\\")
        .replace("{", "\\{")
        .replace("}", "\\}")
        .replace("\n", " ")
        .replace("\r", " ")
    )


def _ass_time(seconds: float) -> str:
    seconds=max(0.0,float(seconds))
    h=int(seconds//3600)
    m=int((seconds%3600)//60)
    s=seconds%60
    return f"{h}:{m:02d}:{s:05.2f}"


def _write_ranking_ass(path: Path, title: str, entries: list[dict], per_scene: float, total_duration: float):
    path.parent.mkdir(parents=True,exist_ok=True)
    lines=[
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Title,DejaVu Sans,52,&H00FFFFFF,&H00FFFFFF,&H00101010,&H00000000,-1,0,0,0,100,100,0,0,1,2,2,7,62,40,40,1",
        "Style: Rank,DejaVu Sans,64,&H00FFFFFF,&H00FFFFFF,&H00101010,&H00000000,-1,0,0,0,100,100,0,0,1,2,2,7,62,40,40,1",
        "Style: Name,DejaVu Sans,31,&H00FFFFFF,&H00FFFFFF,&H00101010,&H00000000,0,0,0,0,100,100,0,0,1,2,2,7,145,40,40,1",
        "Style: ActiveRank,DejaVu Sans,72,&H0000FFFF,&H0000FFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,3,3,7,58,40,40,1",
        "Style: ActiveName,DejaVu Sans,34,&H0000FFFF,&H0000FFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,3,3,7,141,40,40,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    lines.append(f"Dialogue: 0,0:00:00.00,{_ass_time(total_duration)},Title,,0,0,0,,{_ass_escape(title or 'TOP 5')}")
    for pos,entry in enumerate(entries):
        rank=int(entry.get("rank",pos+1))
        name=_ass_escape(entry.get("name") or f"Rank {rank}")
        y=255+pos*205
        lines.append(f"Dialogue: 0,0:00:00.00,{_ass_time(total_duration)},Rank,,0,0,0,,{{\\pos(62,{y})}}{rank}")
        lines.append(f"Dialogue: 0,0:00:00.00,{_ass_time(total_duration)},Name,,0,0,0,,{{\\pos(145,{y+12})}}{name}")
        scene_index=max(0,5-rank)
        start=scene_index*per_scene
        end=min(total_duration,(scene_index+1)*per_scene)
        lines.append(f"Dialogue: 1,{_ass_time(start)},{_ass_time(end)},ActiveRank,,0,0,0,,{{\\pos(58,{y-4})}}{rank}")
        lines.append(f"Dialogue: 1,{_ass_time(start)},{_ass_time(end)},ActiveName,,0,0,0,,{{\\pos(141,{y+9})}}{name}")
    path.write_text("\n".join(lines)+"\n",encoding="utf-8")


def concat_scenes(scenes: list[Path], output: Path):
    if not scenes:
        raise RuntimeError("No scenes to concatenate.")

    # Do not use the concat demuxer here. Some stock-video files carry bad
    # timestamps/metadata that can make the assembled duration explode.
    inputs=[]
    filters=[]
    for i,path in enumerate(scenes):
        inputs += ["-i",str(path)]
        filters.append(
            f"[{i}:v:0]setpts=PTS-STARTPTS,trim=duration=99999,"
            f"scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,setsar=1,fps=30,format=yuv420p[v{i}]"
        )
    labels="".join(f"[v{i}]" for i in range(len(scenes)))
    filters.append(f"{labels}concat=n={len(scenes)}:v=1:a=0,setpts=PTS-STARTPTS[v]")
    subprocess.run(
        ["ffmpeg","-y",*inputs,"-filter_complex",";".join(filters),"-map","[v]",
         "-an","-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p",
         "-r","30","-fps_mode","cfr",str(output)],
        check=True
    )


def add_voice(video: Path,voice: Path,output: Path):
    # Explicitly match video to narration duration. Do not let -shortest decide
    # which stream wins when source timestamps are unusual.
    subprocess.run([
        "ffmpeg","-y","-i",str(video),"-i",str(voice),
        "-map","0:v:0","-map","1:a:0",
        "-c:v","copy","-c:a","aac","-b:a","192k",
        "-shortest",str(output)
    ],check=True)


def apply_ranking_overlay(video: Path, storyboard: dict, output: Path, total_duration: float):
    entries=storyboard.get("ranking_entries") or []
    if not entries:
        entries=[]
        for i,scene in enumerate(storyboard.get("scenes",[]),1):
            entries.append({"rank":i,"name":scene.get("name") or scene.get("purpose") or f"Entry {i}"})
    entries=sorted(entries,key=lambda x:int(x.get("rank",0)))[:5]
    if not entries:
        video.replace(output)
        return

    scenes=storyboard.get("scenes",[])
    per_scene=total_duration/max(len(scenes),1)
    ass_path=output.with_suffix(".ass")
    _write_ranking_ass(ass_path,storyboard.get("title") or "TOP 5",entries,per_scene,total_duration)

    # No solid background panel: the leaderboard is transparent text over the
    # actual footage. Only the active row changes color.
    vf=f"ass=filename={ass_path.resolve()}"
    subprocess.run([
        "ffmpeg","-y","-i",str(video),"-vf",vf,
        "-c:v","libx264","-preset","medium","-crf","18",
        "-pix_fmt","yuv420p","-an",str(output)
    ],check=True)


def final_master(video: Path,output: Path):
    subprocess.run([
        "ffmpeg","-y","-i",str(video),
        "-vf","eq=contrast=1.04:saturation=1.06:brightness=0.01,unsharp=5:5:0.35",
        "-c:v","libx264","-preset","veryfast","-crf","19","-threads","2",
        "-c:a","aac","-b:a","192k","-movflags","+faststart",str(output)
    ],check=True)


def validate(video: Path)->dict:
    import json
    raw=subprocess.check_output([
        "ffprobe","-v","error","-show_entries","stream=width,height,codec_name,duration",
        "-of","json",str(video)
    ],text=True)
    v=next(s for s in json.loads(raw)["streams"] if s.get("width"))
    return {
        "width":v["width"],
        "height":v["height"],
        "codec":v["codec_name"],
        "duration":float(v.get("duration") or 0),
        "vertical":v["height"]>v["width"]
    }
