import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

FAL_KEY=os.getenv("FAL_KEY","")
GEMINI_API_KEY=os.getenv("GEMINI_API_KEY","")
GEMINI_MODEL=os.getenv("GEMINI_MODEL","gemini-2.5-flash")
YOUTUBE_API_KEY=os.getenv("YOUTUBE_API_KEY","")
TREND_REGION=os.getenv("TREND_REGION","US")
TREND_LOOKBACK_HOURS=int(os.getenv("TREND_LOOKBACK_HOURS","24"))
DISCORD_WEBHOOK_URL=os.getenv("DISCORD_WEBHOOK_URL","")
DISCORD_WEBHOOK_VIDEO_URL=os.getenv("DISCORD_WEBHOOK_VIDEO_URL","")
VOICE=os.getenv("VOICE","en-US-GuyNeural")
VIDEO_MODEL=os.getenv("VIDEO_MODEL","minimax/h3-max/text-to-video")
VIDEO_RESOLUTION=os.getenv("VIDEO_RESOLUTION","768P")
VIDEO_SCENE_SECONDS=int(os.getenv("VIDEO_SCENE_SECONDS","5"))
VIDEO_SCENES=int(os.getenv("VIDEO_SCENES","6"))
VIDEO_ASPECT_RATIO=os.getenv("VIDEO_ASPECT_RATIO","9:16")
OUTPUT_DIR=Path(os.getenv("OUTPUT_DIR","output"))

def validate():
    if not FAL_KEY:
        raise RuntimeError("FAL_KEY is required.")
