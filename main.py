import argparse,json,sys,time,uuid,re,subprocess
from config import OUTPUT_DIR,validate
from storyboard import create_storyboard
from ai_video import generate_scene
from audio import make_voiceover
from captions import make_srt,burn_captions,duration as media_duration
from render60 import concat_scenes,add_voice,final_master,validate as validate_video

def build(topic:str, selected_trend=None, hook_override=None, hook_variants=None, longform=False, style_notes=""):
    validate()
    run_id=time.strftime("%Y%m%d-%H%M%S")+"-"+uuid.uuid4().hex[:6]
    root=OUTPUT_DIR/run_id; scenes_dir=root/"scenes"; root.mkdir(parents=True,exist_ok=True)
    print(f"[pipeline] started: {topic}",flush=True)
    creative_topic=topic+(f"\nCreative style notes: {style_notes}" if style_notes.strip() else "")
    storyboard=create_storyboard(creative_topic,hook_override,longform=longform)
    # Keep the storyboard's actual distinct scenes. Never clone generic filler shots.
    if hook_override: storyboard["hook"]=hook_override
    storyboard["hook_variants"]=hook_variants or [storyboard.get("hook","")]
    storyboard["style_notes"]=style_notes
    (root/"storyboard.json").write_text(json.dumps(storyboard,indent=2),encoding="utf-8")
    print(f"[pipeline] storyboard ready: {storyboard.get('format')} / {len(storyboard['scenes'])} scenes",flush=True)

    narration_text=storyboard.get("hook","") if storyboard.get("format")=="ranking" else storyboard.get("script","")
    if not narration_text.strip(): raise ValueError("No narration text available for this video.")
    voice=root/"voice.wav"; make_voiceover(narration_text,voice)
    narration_duration=media_duration(voice)
    if storyboard.get("format")=="ranking":
        per_scene=5.0; visual_duration=per_scene*len(storyboard["scenes"])
    elif storyboard.get("format") in ("longform","tierlist"):
        visual_duration=max(narration_duration+1.0,len(storyboard["scenes"])*6.0)
        per_scene=visual_duration/max(len(storyboard["scenes"]),1)
    else:
        visual_duration=narration_duration+0.75
        per_scene=visual_duration/max(len(storyboard["scenes"]),1)

    scene_paths=[]; scene_meta=[]
    for index,scene in enumerate(storyboard["scenes"],1):
        scene=dict(scene); scene["duration"]=round(per_scene,3)
        scene["aspect"]="landscape" if storyboard.get("format") in ("longform","tierlist") else "vertical"
        path=scenes_dir/f"scene_{index:02d}.mp4"
        print(f"[pipeline] rendering 60 fps scene {index}/{len(storyboard['scenes'])}: {scene.get('purpose','')} ({scene['duration']}s)",flush=True)
        meta=generate_scene(scene.get("prompt",""),path,topic=topic,scene=scene,index=index,duration=scene["duration"])
        scene_paths.append(path); scene_meta.append({**scene,**meta})

    width,height=(1920,1080) if storyboard.get("format") in ("longform","tierlist") else (1080,1920)
    raw=root/"assembled.mp4"; concat_scenes(scene_paths,raw,width=width,height=height)
    # Ranking/tier-list overlays are optional editorial layers; base footage is still generated locally.
    visual_master=raw
    if storyboard.get("format")=="ranking":
        from render import apply_ranking_overlay
        ranked=root/"ranked.mp4"; apply_ranking_overlay(raw,storyboard,ranked,visual_duration); visual_master=ranked
    elif storyboard.get("format")=="tierlist":
        from render import apply_tier_overlay
        tiered=root/"tiered.mp4"; apply_tier_overlay(raw,storyboard,tiered,visual_duration); visual_master=tiered

    voiced=root/"voiced.mp4"; add_voice(visual_master,voice,voiced,duration=visual_duration)
    srt=root/"captions.srt"; make_srt(narration_text,voice,srt)
    captioned=root/"captioned.mp4"; burn_captions(voiced,srt,captioned)
    final=root/"final.mp4"; final_master(captioned,final)

    # Deliver a thumbnail and ready-to-paste social copy alongside the video.
    thumbnail=root/"thumbnail.jpg"
    thumb_time=min(max(0.8,visual_duration*0.18),max(0.1,visual_duration-0.1))
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-ss",str(thumb_time),"-i",str(final),"-frames:v","1","-q:v","2",str(thumbnail)],check=True)
    hashtags=[]
    for word in re.findall(r"[A-Za-z0-9]+",topic):
        tag="#"+word.lower()
        if len(tag)>1 and tag not in hashtags: hashtags.append(tag)
    hashtags=(hashtags[:6]+["#shorts","#learnontiktok","#viral"])[:9]
    social=root/"captions-hashtags.txt"
    social.write_text("CAPTION\n"+narration_text.strip()+"\n\nHASHTAGS\n"+" ".join(hashtags)+"\n",encoding="utf-8")

    qc=validate_video(final)
    expected=(1920,1080) if storyboard.get("format") in ("longform","tierlist") else (1080,1920)
    if (qc["width"],qc["height"])!=expected: raise RuntimeError(f"Final video failed {expected[0]}x{expected[1]} QC: "+str(qc))
    manifest={"run_id":run_id,"topic":topic,"style_notes":style_notes,"title":storyboard.get("title"),"hook":storyboard.get("hook"),
      "hook_variants":storyboard.get("hook_variants",[]),"format":storyboard.get("format"),"ranking_entries":storyboard.get("ranking_entries",[]),
      "tier_entries":storyboard.get("tier_entries",[]),"script":storyboard.get("script"),"trend":selected_trend,"scenes":scene_meta,
      "generation":{"mode":"hosted_ltx_text_to_video","voice":"kokoro_local","scene_count":len(scene_paths),"fps":60,"external_video_generation":True,"free_hosted_gpu":True},
      "qc":qc,"files":{"video":str(final),"thumbnail":str(thumbnail),"storyboard":str(root/"storyboard.json"),"captions":str(srt),"social_copy":str(social)}}
    (root/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(f"[pipeline] QC passed: {qc}",flush=True)
    return final

if __name__=="__main__":
    parser=argparse.ArgumentParser(description="Generate original 60 fps short-form videos.")
    parser.add_argument("--topic",help="Topic to generate. Omit for autonomous trend mode.")
    parser.add_argument("--style-notes",default="",help="Optional visual/editing direction.")
    parser.add_argument("--autopilot",action="store_true",help="Discover a fresh topic and generate automatically.")
    parser.add_argument("--longform",action="store_true",help="Generate a landscape long-form YouTube video.")
    args=parser.parse_args()
    try:
        if args.autopilot or not args.topic:
            from autopilot import run
            print("VIDEO_READY="+str(run()))
        else:
            print("VIDEO_READY="+str(build(args.topic,longform=args.longform,style_notes=args.style_notes)))
    except Exception as exc:
        print("ERROR:",exc,file=sys.stderr); raise
