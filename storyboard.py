
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

def fallback(topic: str, hook_override: str | None = None) -> dict[str, Any]:
    hook=hook_override or f"You probably don't know this about {topic}."
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
    return {"title":topic,"hook":hook,"script":f"Here is the part about {topic} that most people miss. First, understand what is actually happening. Then look at why it matters. The surprising part is what happens next. Once you see the pattern, the whole story makes much more sense.","scenes":scenes}

def create_storyboard(topic: str, hook_override: str | None = None) -> dict[str, Any]:
    if not GEMINI_API_KEY:
        return fallback(topic, hook_override)
    prompt=f"""Topic: {topic}
Preferred hook: {hook_override or "create the strongest curiosity hook yourself"}
Create a {VIDEO_SCENES}-scene vertical short.
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
        return result if len(result.get("scenes",[]))==VIDEO_SCENES else fallback(topic,hook_override)
    except (requests.RequestException, KeyError, IndexError, json.JSONDecodeError) as exc:
        print(f"Gemini storyboard unavailable ({exc}); using local fallback storyboard.")
        return fallback(topic,hook_override)
