import argparse,json,sys,time,uuid
from config import OUTPUT_DIR,validate
from storyboard import create_storyboard
from ai_video import generate_scene
from audio import make_voiceover
from captions import make_srt,burn_captions
from render import concat_scenes,add_voice,final_master,validate as validate_video
from discord_notify import stage,completed

def build(topic:str, selected_trend=None, hook_override=None, hook_variants=None):
    validate()
    run_id=time.strftime("%Y%m%d-%H%M%S")+"-"+uuid.uuid4().hex[:6]
    root=OUTPUT_DIR/run_id; scenes_dir=root/"scenes"; root.mkdir(parents=True,exist_ok=True)
    stage("Pipeline started","Building a $0 locally-rendered vertical short.",topic=topic,run_id=run_id,
          mode="autonomous" if selected_trend else "manual")
    storyboard=create_storyboard(topic,hook_override)
    if hook_override: storyboard["hook"]=hook_override
    storyboard["hook_variants"]=hook_variants or [storyboard.get("hook","")]
    (root/"storyboard.json").write_text(json.dumps(storyboard,indent=2),encoding="utf-8")
    if selected_trend:
        (root/"trend.json").write_text(json.dumps(selected_trend,indent=2),encoding="utf-8")
        stage("Trend selected","Autopilot selected a fresh short-form topic.",source=selected_trend.get("source",""),score=selected_trend.get("score",0))
    stage("Storyboard ready","Creative director produced the story and shot list.",hook=storyboard.get("hook",""),scenes=len(storyboard["scenes"]))
    scene_paths=[]; scene_meta=[]
    for index,scene in enumerate(storyboard["scenes"],1):
        stage("Rendering scene",f"Local generated visual {index}/{len(storyboard['scenes'])}.",scene=index,purpose=scene.get("purpose",""))
        path=scenes_dir/f"scene_{index:02d}.mp4"
        meta=generate_scene(scene["prompt"],path,topic=topic,scene=scene,index=index)
        scene_paths.append(path); scene_meta.append({**scene,**meta})
    raw=root/"assembled.mp4"; concat_scenes(scene_paths,raw)
    voice=root/"voice.mp3"; make_voiceover(storyboard["script"],voice)
    voiced=root/"voiced.mp4"; add_voice(raw,voice,voiced)
    srt=root/"captions.srt"; make_srt(storyboard["script"],voice,srt)
    captioned=root/"captioned.mp4"; burn_captions(voiced,srt,captioned)
    final=root/"final.mp4"; final_master(captioned,final)
    qc=validate_video(final)
    if not(qc["vertical"] and qc["width"]==1080 and qc["height"]==1920):
        raise RuntimeError("Final video failed 1080x1920 vertical QC: "+str(qc))
    manifest={"run_id":run_id,"topic":topic,"title":storyboard.get("title"),
      "hook":storyboard.get("hook"),"hook_variants":storyboard.get("hook_variants",[]),
      "script":storyboard.get("script"),"trend":selected_trend,"scenes":scene_meta,
      "generation":{"mode":"local_procedural","all_scenes_locally_generated":True,"scene_count":len(scene_paths),"external_video_generation":False},
      "qc":qc,"files":{"video":str(final),"storyboard":str(root/"storyboard.json"),"captions":str(srt)}}
    manifest_path=root/"manifest.json"
    manifest_path.write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    completed(topic,final,manifest_path,len(scene_paths))
    stage("QC passed","Final video is 1080x1920 and ready.",codec=qc["codec"])
    return final

if __name__=="__main__":
    parser=argparse.ArgumentParser(description="Generate an original $0 vertical video.")
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
        stage("Pipeline failed",str(exc),topic=args.topic or "autopilot")
        print("ERROR:",exc,file=sys.stderr); raise
