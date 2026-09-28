import argparse,json,sys,time,uuid
from config import OUTPUT_DIR,validate
from storyboard import create_storyboard
from ai_video import generate_scene
from audio import make_voiceover
from captions import make_srt,burn_captions,duration as media_duration
from render import concat_scenes,add_voice,apply_ranking_overlay,final_master,validate as validate_video

def build(topic:str, selected_trend=None, hook_override=None, hook_variants=None):
    validate()
    run_id=time.strftime("%Y%m%d-%H%M%S")+"-"+uuid.uuid4().hex[:6]
    root=OUTPUT_DIR/run_id; scenes_dir=root/"scenes"; root.mkdir(parents=True,exist_ok=True)
    print(f"[pipeline] started: {topic}")

    storyboard=create_storyboard(topic,hook_override)
    if hook_override: storyboard["hook"]=hook_override
    storyboard["hook_variants"]=hook_variants or [storyboard.get("hook","")]
    (root/"storyboard.json").write_text(json.dumps(storyboard,indent=2),encoding="utf-8")
    print(f"[pipeline] storyboard ready: {storyboard.get('format')} / {len(storyboard['scenes'])} scenes")

    # Ranking videos use the hook only; other formats use the full script.
    narration_text = storyboard.get("hook","") if storyboard.get("format") == "ranking" else storyboard.get("script","")
    if not narration_text.strip():
        raise ValueError("No narration text available for this video.")
    voice=root/"voice.wav"
    make_voiceover(narration_text,voice)
    narration_duration=media_duration(voice)
    visual_duration=narration_duration+0.75
    per_scene=visual_duration/max(len(storyboard["scenes"]),1)

    scene_paths=[]; scene_meta=[]
    for index,scene in enumerate(storyboard["scenes"],1):
        scene=dict(scene)
        scene["duration"]=round(per_scene,3)
        path=scenes_dir/f"scene_{index:02d}.mp4"
        print(f"[pipeline] rendering scene {index}/{len(storyboard['scenes'])}: {scene.get('purpose','')} ({scene['duration']}s)")
        meta=generate_scene(scene["prompt"],path,topic=topic,scene=scene,index=index,duration=scene["duration"])
        scene_paths.append(path)
        scene_meta.append({**scene,**meta})

    raw=root/"assembled.mp4"
    concat_scenes(scene_paths,raw)

    # Ranking videos get a persistent 1→5 leaderboard while playback runs 5→1.
    visual_master=raw
    if storyboard.get("format")=="ranking":
        ranked=root/"ranked.mp4"
        apply_ranking_overlay(raw,storyboard,ranked,visual_duration)
        visual_master=ranked

    voiced=root/"voiced.mp4"
    add_voice(visual_master,voice,voiced)

    srt=root/"captions.srt"
    make_srt(narration_text,voice,srt)
    captioned=root/"captioned.mp4"
    burn_captions(voiced,srt,captioned)

    final=root/"final.mp4"
    final_master(captioned,final)

    qc=validate_video(final)
    if not(qc["vertical"] and qc["width"]==1080 and qc["height"]==1920):
        raise RuntimeError("Final video failed 1080x1920 vertical QC: "+str(qc))

    manifest={
        "run_id":run_id,
        "topic":topic,
        "title":storyboard.get("title"),
        "hook":storyboard.get("hook"),
        "hook_variants":storyboard.get("hook_variants",[]),
        "format":storyboard.get("format"),
        "ranking_entries":storyboard.get("ranking_entries",[]),
        "script":storyboard.get("script"),
        "trend":selected_trend,
        "scenes":scene_meta,
        "generation":{
            "mode":"pexels_stock_video",
            "voice":"kokoro_local",
            "ranking_overlay":storyboard.get("format")=="ranking",
            "scene_count":len(scene_paths),
            "external_video_generation":False
        },
        "qc":qc,
        "files":{"video":str(final),"storyboard":str(root/"storyboard.json"),"captions":str(srt)}
    }
    manifest_path=root/"manifest.json"
    manifest_path.write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(f"[pipeline] QC passed: {qc}")
    return final

if __name__=="__main__":
    parser=argparse.ArgumentParser(description="Generate an original vertical short.")
    parser.add_argument("--topic",help="Topic to generate. Omit for autonomous trend mode.")
    parser.add_argument("--autopilot",action="store_true",help="Discover a fresh topic and generate automatically.")
    args=parser.parse_args()
    try:
        if args.autopilot or not args.topic:
            from autopilot import run
            print("VIDEO_READY="+str(run()))
        else:
            print("VIDEO_READY="+str(build(args.topic)))
    except Exception as exc:
        print("ERROR:",exc,file=sys.stderr)
        raise
