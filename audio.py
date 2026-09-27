import asyncio
from pathlib import Path
import edge_tts
from config import VOICE

async def _make_voice(text: str, output: str):
    await edge_tts.Communicate(text, VOICE).save(output)

def make_voiceover(text: str, output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    asyncio.run(_make_voice(text, str(output_path)))
