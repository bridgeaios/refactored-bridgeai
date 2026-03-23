"""Twins domain service facade (used by tests and optional thin routes)."""
from __future__ import annotations

from typing import Any, Optional

from app.services.bossbots import BossBotsService
from app.services.cognitive_twin import CognitiveTwinService
from app.services.emotion import EmotionService
from app.services.speech_embodiment import SpeechEmbodimentService
from app.services.speech_reasoning import SpeechReasoningService
from app.services.twins_competition import TwinsCompetitionService


class TwinsServices:
    """Aggregates twins-domain services."""

    def __init__(self) -> None:
        self._twin = CognitiveTwinService()
        self._emotion = EmotionService()
        self._competition = TwinsCompetitionService()
        self._speech_em = SpeechEmbodimentService()
        self._speech_re = SpeechReasoningService()
        self._bossbots = BossBotsService()

    def get_profile(self, twin_id: str = "default") -> dict[str, Any]:
        profile = self._twin.get_profile()
        if isinstance(profile, dict):
            return {**profile, "twin_id": twin_id}
        return {"twin_id": twin_id, "status": "active"}

    async def decide(
        self,
        prompt: str,
        twin_id: str = "default",
        context: Optional[dict] = None,
    ) -> dict[str, Any]:
        _ = twin_id
        env = {"prompt": prompt, **(context or {})}
        result = self._twin.decide(env, [], set(), 0.5, [])
        if result is None:
            return {"ok": True, "action": None, "reason": "no_positive_value_output"}
        return {"ok": True, **(result if isinstance(result, dict) else {"decision": str(result)})}

    async def shared_xml(self) -> str:
        from app.core.deps import get_memory

        mem = get_memory()
        xml = await mem.get("twin:shared_xml")
        return xml or ""

    async def emotion_status(self, twin_id: str) -> dict[str, Any]:
        return {"twin_id": twin_id, "state": "neutral"}

    async def emotion_update(self, twin_id: str, emotion: str, intensity: float) -> dict[str, Any]:
        _ = emotion
        _ = intensity
        return {"ok": True, "twin_id": twin_id}

    async def speak(
        self,
        text: str,
        twin_id: str = "default",
        voice: Optional[str] = None,
    ) -> dict[str, Any]:
        _ = twin_id
        _ = voice
        embody, _plan = self._speech_em.process(text, context={}, audience_model={})
        return {"ok": True, "text": embody.text, "silence": embody.silence}

    async def speech_reason(self, prompt: str, context: Optional[dict] = None) -> dict[str, Any]:
        result = self._speech_re.process(prompt, context=context or {})
        return self._speech_re.to_dict(result)

    async def competition_status(self) -> dict[str, Any]:
        return {"ok": True, "leaderboard": self._competition.get_leaderboard()}

    async def competition_submit(self, twin_id: str, round_id: str, answer: str) -> dict[str, Any]:
        _ = twin_id
        _ = round_id
        _ = answer
        return {"ok": True}

    def list_bossbots(self) -> list[dict]:
        return self._bossbots.get_signals()
