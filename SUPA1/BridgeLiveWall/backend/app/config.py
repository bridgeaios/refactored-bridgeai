import os

ALLOWED_ORIGINS = ["http://localhost:3000"]
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
LOCAL_TTS_URL = os.getenv("LOCAL_TTS_URL")
