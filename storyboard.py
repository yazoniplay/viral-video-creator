import json
from typing import Any
import requests
from config import GEMINI_API_KEY, GEMINI_MODEL, VIDEO_SCENES

SYSTEM = """You are a senior short-form video creative director.
Create original, high-retention vertical video concepts designed to be genuinely watchable.
Every scene must use VIDEO FOOTAGE ONLY. Never request still images, image slideshows, screenshots, illustrations, photo montages, or static graphics as the visual.
For stock-footage scenes, every visual prompt must describe a concrete subject and moving action that can be searched as a real stock VIDEO clip on Pexels.
Avoid copyrighted characters, logos and watermarks.
For ranking videos, create a persistent leaderboard: ranks are displayed visually from 1 at the top to 5 at the bottom, but the actual clips play from 5 to 1. All five entries remain visible for the entire video; only the active row is highlighted.
The ranking should feel like an actual editorial ranking with distinct named entries, not generic labels.
Return only valid JSON."""

def is_ranking_topic(topic: str) -> bool:
    t=topic.lower()
    return any(x in t for x in ("top ", "top 5", "top 10", "ranking", "ranked", "funniest", "funny moments", "best moments", "worst moments", "countdown"))

def fallback(topic: str, hook_override: str | None = None) -> dict[str, Any]:
    ranking=is_ranking_topic(topic)
    hook=hook_override or (f"These are the moments that deserve the top spots in {topic}." if ranking else f"You probably don't know this about {topic}.")
    if ranking:
        count=5
        names=[
            "The Warm-Up",
            "The Clean Landing",
            "The Near Miss",
            "The Impossible Gap",
            "The Perfect Run",
        ]
        rank_entries=[{"rank":i,"name":names[5-i]} for i in range(1,6)]
        rank_to_prompt={
            5:"a simple but impressive parkour movement with a clean landing",
            4:"a fast parkour run with a more difficult obstacle",
            3:"a technical parkour sequence with a risky-looking but controlled jump",
            2:"an extremely difficult parkour gap with a dramatic landing",
            1:"an extraordinary parkour sequence with a spectacular clean finish"
        }
        scenes=[]
        for playback_rank in range(5,0,-1):
            entry=next(x for x in rank_entries if x["rank"]==playback_rank)
            scenes.append({
                "duration":5,
                "purpose":f"rank {playback_rank}",
                "rank":playback_rank,
                "name":entry["name"],
                "camera":"dynamic handheld tracking",
                "prompt":f"Realistic vertical stock VIDEO footage of {rank_to_prompt[playback_rank]}, continuous visible motion, athletic movement, clear beginning and landing, no text, no logos."
            })
        script=""
        return {"title":topic,"hook":hook,"script":script,"format":"ranking","ranking_count":5,
                "ranking_entries":rank_entries,"scenes":scenes}

    prompts=[
        ("instant visual hook","fast push-in",f"Realistic vertical stock VIDEO footage about {topic}; immediate physical action, surprising subject, clear motion, no text, no logos."),
        ("establish context","lateral tracking",f"Realistic vertical stock VIDEO footage showing the world around {topic}; concrete subject performing a visible action, natural motion, no text, no logos."),
        ("first key idea","controlled orbit",f"Realistic vertical stock VIDEO footage demonstrating the first important idea behind {topic} through a physical action, detailed and believable, no text."),
        ("escalation","low-angle tracking",f"Realistic vertical stock VIDEO footage connected to {topic}; increasing scale and motion, dramatic but believable action, no text, no logos."),
        ("surprising payoff","rapid reveal then close-up",f"Realistic vertical stock VIDEO footage of a surprising reveal connected to {topic}; clear cause and effect, visible movement, no text."),
        ("loopable ending","slow pull-back",f"Realistic vertical stock VIDEO footage about {topic} that echoes the opening subject and motion, smooth movement, no text, no logos.")
    ]
    scenes=[{"duration":5,"purpose":p,"camera":c,"prompt":x,"continuity":"Keep visual language and the main subject coherent."} for p,c,x in prompts[:VIDEO_SCENES]]
    while len(scenes)<VIDEO_SCENES: scenes.append(scenes[-1].copy())
    return {"title":topic,"hook":hook,"script":f"Here is the part about {topic} that most people miss. First, understand what is actually happening. Then look at why it matters. The surprising part is what happens next. Once you see the pattern, the whole story makes much more sense.","format":"explainer","scenes":scenes}

def create_storyboard(topic: str, hook_override: str | None = None) -> dict[str, Any]:
    if not GEMINI_API_KEY:
        return fallback(topic, hook_override)
    ranking=is_ranking_topic(topic)
    prompt=f"""Topic: {topic}
Preferred hook: {hook_override or "create the strongest curiosity hook yourself"}
Create a short vertical video. Format: {"ranking" if ranking else "explainer"}.

If ranking format:
- Rank exactly 5 entries.
- Return ranking_entries with exactly five objects containing rank and name.
- The leaderboard order is ALWAYS 1, 2, 3, 4, 5 from top to bottom.
- Playback order is ALWAYS 5, 4, 3, 2, 1.
- All five rows stay visible for the entire video.
- Each scene must contain rank and name matching its entry.
- Scenes must be returned in playback order: 5, 4, 3, 2, 1.
- Give each entry a short, interesting name that actually describes what is being ranked.
- Make the #1 entry the strongest payoff.
- Do NOT write a narration script for ranking videos.
- The hook is the ONLY spoken narration; make it short, punchy, and curiosity-driven.
- Never ask the stock-video search for text, number badges, UI, logos, or graphics; the renderer adds the leaderboard.

For every video:
- For non-ranking videos, write 90-130 words of natural spoken narration.
- For ranking videos, write ONLY a strong hook in the hook field; do not create a script.
- Every scene must describe a distinct moving VIDEO event.
- Every scene prompt must work as a real Pexels stock VIDEO search query.
- Never request still images or static graphics.
- Keep the visuals tightly connected to what is being said.
Return JSON keys: title, hook, script, format, ranking_entries, scenes."""

    url="https://generativelanguage.googleapis.com/v1beta/models/"+GEMINI_MODEL+":generateContent"
    try:
        response=requests.post(url,headers={"x-goog-api-key":GEMINI_API_KEY,"Content-Type":"application/json"},json={
            "systemInstruction":{"parts":[{"text":SYSTEM}]},
            "contents":[{"parts":[{"text":prompt}]}],
            "generationConfig":{"temperature":0.95,"responseMimeType":"application/json"}
        },timeout=90)
        response.raise_for_status()
        text=response.json()["candidates"][0]["content"]["parts"][0]["text"]
        result=json.loads(text)
        scenes=result.get("scenes", [])
        normalized=[]
        for i,scene in enumerate(scenes,1):
            if not isinstance(scene,dict):
                continue
            purpose=str(scene.get("purpose") or scene.get("title") or f"Scene {i}")
            prompt_text=scene.get("prompt") or scene.get("visual_prompt") or scene.get("description") or purpose
            normalized.append({**scene,"purpose":purpose,"prompt":str(prompt_text),"duration":int(scene.get("duration",5) or 5)})
        if ranking:
            entries=result.get("ranking_entries") or []
            clean=[]
            for entry in entries:
                if isinstance(entry,dict) and str(entry.get("name","")).strip():
                    try: rank=int(entry.get("rank"))
                    except (TypeError,ValueError): continue
                    if 1 <= rank <= 5: clean.append({"rank":rank,"name":str(entry["name"]).strip()})
            clean=sorted({x["rank"]:x for x in clean}.values(),key=lambda x:x["rank"])
            if len(clean)!=5 or len(normalized)!=5:
                return fallback(topic,hook_override)
            by_rank={int(s.get("rank",0)):s for s in normalized}
            if any(rank not in by_rank for rank in range(1,6)):
                return fallback(topic,hook_override)
            ordered=[]
            for rank in range(5,0,-1):
                s=dict(by_rank[rank])
                entry=next(x for x in clean if x["rank"]==rank)
                s["rank"]=rank
                s["name"]=entry["name"]
                ordered.append(s)
            result["scenes"]=ordered
            result["ranking_entries"]=clean
            result["format"]="ranking"
            return result
        if len(normalized)==VIDEO_SCENES:
            result["scenes"]=normalized
            result["format"]=result.get("format") or "explainer"
            return result
        return fallback(topic,hook_override)
    except (requests.RequestException, KeyError, IndexError, json.JSONDecodeError) as exc:
        print(f"Gemini storyboard unavailable ({exc}); using local fallback storyboard.")
        return fallback(topic,hook_override)
