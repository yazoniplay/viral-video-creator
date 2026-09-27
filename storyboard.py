import json
from typing import Any
import requests
from config import GEMINI_API_KEY, GEMINI_MODEL, VIDEO_SCENES

SYSTEM = """You are a senior short-form video creative director.
Create original, high-retention vertical video concepts.
Every scene must be visually generatable by a text-to-video model.
Avoid copyrighted characters, logos and watermarks.
Return only valid JSON."""

def fallback(topic: str) -> dict[str, Any]:
    prompts = [
        ("instant visual hook", "fast push-in", f"Cinematic vertical opening shot about {topic}; visually surprising subject, immediate motion, strong depth, realistic lighting, premium documentary style, no text, no logos."),
        ("establish context", "lateral tracking", f"Vertical cinematic scene explaining the world around {topic}; clear central subject, layered foreground and background, natural motion, photorealistic, no text, no logos."),
        ("first key idea", "controlled orbit", f"Vertical cinematic visualization of the first important idea behind {topic}; show the concept physically through action rather than labels, highly detailed, realistic motion, no text."),
        ("escalation", "low-angle tracking", f"High-energy vertical cinematic visualization connected to {topic}; increasing scale and motion, dramatic but believable, premium lighting, no text, no logos."),
        ("surprising payoff", "rapid reveal then close-up", f"Visually surprising reveal connected to {topic}; clear cause and effect, cinematic realism, strong contrast and depth, no text."),
        ("loopable ending", "slow pull-back", f"Beautiful final vertical shot about {topic} that echoes the opening composition, cinematic realism, smooth motion, no text, no logos.")
    ]
    scenes = [{"duration":5,"purpose":p,"camera":c,"prompt":x,
               "continuity":"Keep visual language and the main subject coherent."}
              for p,c,x in prompts[:VIDEO_SCENES]]
    while len(scenes) < VIDEO_SCENES:
        scenes.append(scenes[-1].copy())
    return {
        "title": topic,
        "hook": f"You probably don't know this about {topic}.",
        "script": f"Here is the part about {topic} that most people miss. First, understand what is actually happening. Then look at why it matters. The surprising part is what happens next. Once you see the pattern, the whole story makes much more sense.",
        "scenes": scenes
    }

def create_storyboard(topic: str) -> dict[str, Any]:
    if not GEMINI_API_KEY:
        return fallback(topic)
    prompt = f"""Topic: {topic}
Create a {VIDEO_SCENES}-scene vertical short.
The narration should be 90-130 words.
The hook must create curiosity immediately.
Each scene needs duration, purpose, self-contained text-to-video prompt, camera and continuity.
Make the sequence tell a story rather than repeat generic b-roll.
Return JSON keys: title, hook, script, scenes."""
    url = "https://generativelanguage.googleapis.com/v1beta/models/" + GEMINI_MODEL + ":generateContent"
    response = requests.post(
        url,
        params={"key": GEMINI_API_KEY},
        json={
            "systemInstruction": {"parts":[{"text":SYSTEM}]},
            "contents": [{"parts":[{"text":prompt}]}],
            "generationConfig": {"temperature":0.9,"responseMimeType":"application/json"}
        },
        timeout=90
    )
    response.raise_for_status()
    text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
    result = json.loads(text)
    return result if len(result.get("scenes", [])) == VIDEO_SCENES else fallback(topic)
