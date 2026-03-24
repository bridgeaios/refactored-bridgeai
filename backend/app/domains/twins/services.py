"""Twins domain service facade."""
from __future__ import annotations

from typing import Any

from app.services.bossbots import BossBotsService
from app.services.cognitive_twin import CognitiveTwinService
from app.services.emotion import EmotionService
from app.services.learning import LearningService
from app.services.speech_embodiment import SpeechEmbodimentService
from app.services.speech_reasoning import SpeechReasoningService
from app.services.twins_competition import TwinsCompetitionService


class TwinsServices:
    """Aggregates all twins-domain services."""

    def __init__(self) -> None:
        self._twin = CognitiveTwinService()
        self._emotion = EmotionService()
        self._competition = TwinsCompetitionService()
        self._speech_em = SpeechEmbodimentService()
        self._speech_re = SpeechReasoningService()
        self._bossbots = BossBotsService()
        self._learning = LearningService()

    # ------------------------------------------------------------------
    # Twin
    # ------------------------------------------------------------------

    def get_profile(self, twin_id: str = "default") -> dict[str, Any]:
        raw = self._twin.get_profile()
        return {"twin_id": twin_id, "status": "active", **(raw if isinstance(raw, dict) else {})}

    async def decide(self, prompt: str, twin_id: str = "default", context: dict | None = None) -> dict[str, Any]:
        # CognitiveTwinService.decide() takes structured args; use context to build candidates
        ctx = context or {}
        candidates = ctx.get("candidates", [{"expected_value": 1.0, "ethical_compliance": 1.0,
                                              "strategic_alignment": 1.0, "long_term_compounding": 1.0,
                                              "action": prompt}])
        result = self._twin.decide(
            environment=ctx.get("environment", {}),
            goal_vector=ctx.get("goal_vector", [1.0]),
            constraints=set(ctx.get("constraints", [])),
            risk_threshold=ctx.get("risk_threshold", 0.5),
            candidates=candidates,
        )
        decision_text = result.get("action", prompt) if isinstance(result, dict) else prompt
        return {"ok": True, "decision": decision_text, "raw": result}

    async def shared_xml(self) -> str:
        return str(getattr(self._twin, "shared_xml", "") or "")

    # ------------------------------------------------------------------
    # Emotion
    # ------------------------------------------------------------------

    async def emotion_status(self, twin_id: str = "default") -> dict[str, Any]:
        # EmotionService.compute() is async and takes inputs dict
        status = await self._emotion.compute({"twin_id": twin_id})
        return {"twin_id": twin_id, **(status if isinstance(status, dict) else {})}

    async def emotion_update(self, twin_id: str, emotion: str, intensity: float) -> dict[str, Any]:
        await self._emotion.compute({"twin_id": twin_id, "emotion": emotion, "intensity": intensity})
        return {"ok": True}

    # ------------------------------------------------------------------
    # Speech
    # ------------------------------------------------------------------

    async def speak(self, text: str, twin_id: str = "default", voice: str | None = None) -> dict[str, Any]:
        if hasattr(self._speech_em, "speak"):
            result = await self._speech_em.speak(text=text, twin_id=twin_id, voice=voice)
            return result if isinstance(result, dict) else {"ok": True, "text": text}
        return {"ok": True, "text": text}

    async def speech_reason(self, prompt: str, context: dict | None = None) -> dict[str, Any]:
        if hasattr(self._speech_re, "reason"):
            result = await self._speech_re.reason(prompt=prompt, context=context or {})
            return result if isinstance(result, dict) else {"ok": True, "result": str(result)}
        return {"ok": True, "reasoning": ""}

    # ------------------------------------------------------------------
    # Competition
    # ------------------------------------------------------------------

    async def competition_status(self) -> dict[str, Any]:
        leaderboard = self._competition.get_leaderboard()
        twins = self._competition.list_twins()
        return {"ok": True, "leaderboard": leaderboard, "twins": twins}

    async def competition_submit(self, twin_id: str, round_id: str, answer: str) -> dict[str, Any]:
        return {"ok": True, "twin_id": twin_id, "round_id": round_id}

    # ------------------------------------------------------------------
    # Bossbots
    # ------------------------------------------------------------------

    def list_bossbots(self) -> list[dict]:
        return self._bossbots.get_signals()
