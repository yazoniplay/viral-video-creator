import requests
from config import DISCORD_WEBHOOK_URL,DISCORD_WEBHOOK_VIDEO_URL

def send(url,title,description,fields=None):
    if not url:return
    payload={"username":"Viral Video Creator","embeds":[{"title":title,"description":description,
        "color":0x7C3AED,"fields":fields or [],
        "footer":{"text":"Viral Video Creator • AI production pipeline"}}]}
    try:requests.post(url,json=payload,timeout=15).raise_for_status()
    except Exception as exc:print(f"[discord] notification failed: {exc}")

def stage(name,description,**fields):
    send(DISCORD_WEBHOOK_URL,"🎬 "+name,description,
         [{"name":k.replace("_"," ").title(),"value":str(v)[:1024],"inline":True} for k,v in fields.items()])

def completed(topic,output,manifest,scenes):
    send(DISCORD_WEBHOOK_VIDEO_URL or DISCORD_WEBHOOK_URL,"✅ Video ready",
         "**"+topic+"**\n\nThe video passed final render checks.",
         [{"name":"AI-generated scenes","value":str(scenes),"inline":True},
          {"name":"Output","value":str(output),"inline":False},
          {"name":"Manifest","value":str(manifest),"inline":False}])
