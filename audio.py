import base64
from pathlib import Path
import requests
from config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, ELEVENLABS_MODEL

API = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

def make_voiceover(text: str, output_path: Path):
    if not ELEVENLABS_API_KEY:
        raise RuntimeError("ELEVENLABS_API_KEY is missing. Add your ElevenLabs API key to GitHub Actions secrets.")
    if not ELEVENLABS_VOICE_ID:
        raise RuntimeError("ELEVENLABS_VOICE_ID is missing. Add the ElevenLabs voice ID to GitHub Actions secrets.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    url = API.format(voice_id=ELEVENLABS_VOICE_ID)
    response = requests.post(
        url,
        headers={
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        params={"output_format": "mp3_44100_128"},
        json={
            "text": text,
            "model_id": ELEVENLABS_MODEL,
            "voice_settings": {
                "stability": 0.38,
                "similarity_boost": 0.82,
                "style": 0.35,
                "use_speaker_boost": True,
            },
        },
        timeout=120,
    )
    if not response.ok:
        raise RuntimeError(f"ElevenLabs TTS failed ({response.status_code}): {response.text[:1200]}")
    output_path.write_bytes(response.content)
