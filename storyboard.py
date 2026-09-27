
import json
from typing import Any
import requests
from config import GEMINI_API_KEY, GEMINI_MODEL, VIDEO_SCENES

SYSTEM = """You are a senior short-form video creative director.
Create original, high-retention vertical video concepts.
Every scene must be visually generatable by a text-to-video model.
Avoid copyrighted characters, logos and watermarks.
Make the first 2 seconds visually decisive and the final scene loop naturally.
Return only valid JSON."""

def is_ranking_topic(topic: str) -> bool:
    t=topic.lower()
    return any(x in t for x in ("top ", "top 5", "top 10", "ranking", "ranked", "funniest", "funny moments", "best moments", "worst moments", "countdown"))

def fallback(topic: str, hook_override: str | None = None) -> dict[str, Any]:
    ranking=is_ranking_topic(topic)
    hook=hook_override or (f"These are the moments that deserve the top spots in {topic}." if ranking else f"You probably don't know this about {topic}.")
    if ranking:
        rank_prompts=[
            ("countdown opener","A fast vertical countdown intro for {topic}; giant number 5, energetic motion, bold graphic shapes, visual punch, no logos."),
            ("rank 5","Visualize the #5 entry for {topic}; a distinct funny/action scenario, large #5 badge, freeze-frame style moment, dynamic camera, no logos."),
            ("rank 4","Visualize the #4 entry for {topic}; completely different comedic/action scenario, large #4 badge, dynamic camera, expressive motion, no logos."),
            ("rank 3","Visualize the #3 entry for {topic}; escalating absurd or funny scenario, large #3 badge, dramatic reveal, dynamic camera, no logos."),
            ("rank 2","Visualize the #2 entry for {topic}; high-energy standout scenario, large #2 badge, fast push-in, strong visual payoff, no logos."),
            ("rank 1","Visualize the #1 entry for {topic}; biggest payoff, large #1 badge, celebratory ending that can loop into the countdown opener, no logos.")
        ]
        scenes=[{"duration":5,"purpose":p,"camera":"dynamic","prompt":x.format(topic=topic),"continuity":"Each rank must have a visibly different composition and event."} for p,x in rank_prompts[:VIDEO_SCENES]]
        script=f"Here are the top moments in {topic}. Number five starts the countdown. Number four gets even better. Number three is where things get ridiculous. Number two is almost impossible to beat. And number one takes the top spot. Which one would you put first?"
        return {"title":topic,"hook":hook,"script":script,"format":"ranking","scenes":scenes}
    prompts=[
        ("instant visual hook","fast push-in",f"Cinematic vertical opening shot about {topic}; visually surprising subject, immediate motion, strong depth, realistic lighting, premium documentary style, no text, no logos."),
        ("establish context","lateral tracking",f"Vertical cinematic scene explaining the world around {topic}; clear central subject, layered foreground and background, natural motion, photorealistic, no text, no logos."),
        ("first key idea","controlled orbit",f"Vertical cinematic visualization of the first important idea behind {topic}; show the concept physically through action rather than labels, highly detailed, realistic motion, no text."),
        ("escalation","low-angle tracking",f"High-energy vertical cinematic visualization connected to {topic}; increasing scale and motion, dramatic but believable, premium lighting, no text, no logos."),
        ("surprising payoff","rapid reveal then close-up",f"Visually surprising reveal connected to {topic}; clear cause and effect, cinematic realism, strong contrast and depth, no text."),
        ("loopable ending","slow pull-back",f"Beautiful final vertical shot about {topic} that echoes the opening composition, cinematic realism, smooth motion, no text, no logos.")
    ]
    scenes=[{"duration":5,"purpose":p,"camera":c,"prompt":x,"continuity":"Keep visual language and the main subject coherent."} for p,c,x in prompts[:VIDEO_SCENES]]
    while len(scenes)<VIDEO_SCENES: scenes.append(scenes[-1].copy())
    return {"title":topic,"hook":hook,"script":f"Here is the part about {topic} that most people miss. First, understand what is actually happening. Then look at why it matters. The surprising part is what happens next. Once you see the pattern, the whole story makes much more sense.","format":"explainer","scenes":scenes}

def create_storyboard(topic: str, hook_override: str | None = None) -> dict[str, Any]:
    if not GEMINI_API_KEY:
        return fallback(topic, hook_override)
    prompt=f"""Topic: {topic}
Preferred hook: {hook_override or "create the strongest curiosity hook yourself"}
Create a {VIDEO_SCENES}-scene vertical short.\nFormat: {"ranking" if is_ranking_topic(topic) else "explainer"}. If this is a ranking/countdown, each scene must represent a different rank and use a different visual composition.
The narration should be 90-130 words.
The first sentence must create immediate curiosity.
The first scene must be a strong visual hook, not generic b-roll.
Every scene must have a distinct visual event and move the story forward.
The last scene should visually echo the first for a seamless loop.
Return JSON keys: title, hook, script, scenes."""
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
        # Normalize model output so the renderer always receives the fields it needs.
        normalized=[]
        for i, scene in enumerate(scenes[:VIDEO_SCENES], 1):
            if not isinstance(scene, dict):
                continue
            purpose=str(scene.get("purpose") or scene.get("title") or f"Scene {i}")
            prompt_text=scene.get("prompt") or scene.get("visual_prompt") or scene.get("description") or purpose
            normalized.append({**scene, "purpose": purpose, "prompt": str(prompt_text), "duration": int(scene.get("duration", 5) or 5)})
        if len(normalized) == VIDEO_SCENES:
            result["scenes"] = normalized
            result["format"] = result.get("format") or ("ranking" if is_ranking_topic(topic) else "explainer")
            return result
        return fallback(topic,hook_override)
    except (requests.RequestException, KeyError, IndexError, json.JSONDecodeError) as exc:
        print(f"Gemini storyboard unavailable ({exc}); using local fallback storyboard.")
        return fallback(topic,hook_override)
