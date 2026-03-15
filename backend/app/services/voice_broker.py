import os
import aiohttp
import asyncio
from typing import AsyncIterator

ELEVEN_API = os.getenv("ELEVEN_API_KEY")
LOCAL_TTS = os.getenv("LOCAL_TTS_URL")

class VoiceBroker:
    def __init__(self):
        self._session: aiohttp.ClientSession | None = None

    def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def stream_tts(self, text: str, voice_id: str = "21m00Tcm4TlvDq8ikWAM"):
        session = self._get_session()
        if ELEVEN_API:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
            headers = {"xi-api-key": ELEVEN_API, "Content-Type": "application/json"}
            payload = {"text": text}
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    raise RuntimeError("ElevenLabs TTS failed")
                async for chunk in resp.content.iter_chunked(1024):
                    yield chunk
        elif LOCAL_TTS:
            async with session.post(LOCAL_TTS, json={"text": text}) as resp:
                if resp.status != 200:
                    raise RuntimeError("Local TTS failed")
                async for chunk in resp.content.iter_chunked(1024):
                    yield chunk
        else:
            raise RuntimeError("No TTS available")

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
