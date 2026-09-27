import re,subprocess
from pathlib import Path

def duration(path:Path)->float:
    return float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration",
        "-of","default=noprint_wrappers=1:nokey=1",str(path)],text=True).strip())

def stamp(seconds:float)->str:
    ms=int(round(seconds*1000))
    h,ms=divmod(ms,3600000); m,ms=divmod(ms,60000); s,ms=divmod(ms,1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def make_srt(text:str,audio:Path,output:Path):
    words=re.findall(r"\S+",text.strip())
    if not words:return
    chunks=[words[i:i+5] for i in range(0,len(words),5)]
    total=duration(audio); slot=total/len(chunks)
    lines=[]
    for i,chunk in enumerate(chunks):
        lines += [str(i+1),f"{stamp(i*slot)} --> {stamp(min(total,(i+1)*slot))}"," ".join(chunk),""]
    output.write_text("\n".join(lines),encoding="utf-8")

def burn_captions(video:Path,srt:Path,output:Path):
    subtitle=str(srt).replace("\\","/").replace(":","\\:")
    vf=f"subtitles='{subtitle}':force_style='FontName=Arial,FontSize=20,Bold=1,Outline=3,Alignment=2,MarginV=180'"
    subprocess.run(["ffmpeg","-y","-i",str(video),"-vf",vf,"-c:v","libx264","-preset","medium",
        "-crf","18","-c:a","aac","-b:a","192k",str(output)],check=True)
