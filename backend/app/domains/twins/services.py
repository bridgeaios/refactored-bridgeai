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
        from app.runtime import memory as _mem
        twin_xml_key = "twin:shared_xml"
        default_xml = '<?xml version="1.0" encoding="UTF-8"?><twin><authority>I am the Bridge.</authority><backend>human</backend></twin>'
        xml = await _mem.get(twin_xml_key)
        if xml is None:
            xml = default_xml
            await _mem.set(twin_xml_key, xml)
        return str(xml)

    async def set_shared_xml(self, xml: str) -> dict[str, Any]:
        from app.core.errors import ValidationError
        from app.runtime import memory as _mem
        if not xml or not xml.lstrip().startswith("<"):
            raise ValidationError("valid XML required")
        await _mem.set("twin:shared_xml", xml)
        return {"ok": True}

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

    def bossbots_signals(self) -> list[dict[str, Any]]:
        return self._bossbots.get_signals()

    def bossbots_trade(self, asset: str, twin_id: str = "system") -> dict[str, Any]:
        from app.physics import check_economic_risk, record_economic_action
        from app.runtime import (
            bossbots_service,
            revenue_service,
            sdg_service,
            twins_competition,
        )
        amount = 0.05
        allowed, reason = check_economic_risk(twin_id, amount)
        if not allowed:
            from app.core.errors import EconomicGateError
            raise EconomicGateError(reason)
        signal = bossbots_service.generate_signal(asset)
        twin_executions = twins_competition.execute_signal_for_twins(asset, signal)
        collected = revenue_service.collect(0.05, source="bossbots", method="trade")
        if collected:
            record_economic_action(twin_id, amount)
            sdg_service.track("trades_executed", 1)
        return {"signal": signal, "twins_followed": twin_executions}

    # ------------------------------------------------------------------
    # Twins competition
    # ------------------------------------------------------------------

    def list_twins(self) -> list[dict]:
        from app.runtime import twins_competition
        return twins_competition.list_twins()

    def twins_leaderboard(self) -> list[dict]:
        from app.runtime import twins_competition
        return twins_competition.get_leaderboard()

    def twins_auto_add(self) -> dict[str, Any]:
        from app.runtime import marketplace_service, sdg_service, twins_competition
        t = twins_competition.auto_add_task(marketplace_service)
        if not t:
            from app.core.errors import NetworkError
            raise NetworkError("auto-add failed")
        sdg_service.track("tasks_created", 1)
        return {"status": "created", "task": t}

    def twins_allocate(self, task_id: int, twin_id: str) -> dict[str, Any]:
        from app.core.errors import NotFoundError
        from app.runtime import marketplace_service, twins_competition
        t = twins_competition.allocate_task(task_id, twin_id, marketplace_service)
        if not t:
            raise NotFoundError("task not available or twin not found")
        return {"status": "allocated", "task": t}

    def twins_teach(self, teacher_id: str, student_id: str, skill_name: str) -> dict[str, Any]:
        from app.core.errors import NotFoundError
        from app.runtime import twins_competition
        result = twins_competition.teach_skill(teacher_id, student_id, skill_name)
        if not result:
            raise NotFoundError("twin not found or teacher does not have that skill verified")
        return {"status": "taught", **result}

    # ------------------------------------------------------------------
    # Twin simulate / evolve / env-keys
    # ------------------------------------------------------------------

    @staticmethod
    def env_keys() -> dict[str, Any]:
        import os
        checks: list[dict[str, Any]] = [
            {"key": "OPENAI_API_KEY", "label": "OpenAI", "critical": True},
            {"key": "HF_TOKEN", "label": "Hugging Face", "critical": True},
            {"key": "HUGGING_FACE_API_KEY", "label": "Hugging Face (alt)", "critical": True},
            {"key": "CLOUDFLARE_ACCOUNT_ID", "label": "Cloudflare Account", "critical": True},
            {"key": "JWT_SECRET", "label": "JWT Secret", "critical": True},
            {"key": "JWT_SECRET_KEY", "label": "JWT Secret Key", "critical": True},
            {"key": "TURNSTILE_SECRET_KEY", "label": "Cloudflare Turnstile", "critical": False},
            {"key": "ELEVENLABS_API_KEY", "label": "ElevenLabs", "critical": False},
            {"key": "ANTHROPIC_API_KEY", "label": "Anthropic", "critical": False},
            {"key": "SMTP_PASSWORD", "label": "SMTP", "critical": False},
            {"key": "PAYPAL_CLIENT_ID", "label": "PayPal", "critical": False},
            {"key": "DISCORD_BOT_TOKEN", "label": "Discord Bot", "critical": False},
            {"key": "R2_BUCKET_NAME", "label": "Cloudflare R2 Bucket", "critical": False},
        ]
        placeholders = ("your-", "sk-your-", "hf_your", "your_", "generate-a-strong",
                        "change-me", "your-cloudflare", "sk_test_", "pk_test_")
        result = []
        for c in checks:
            val = os.environ.get(c["key"]) or ""
            if not val or len(val) < 8:
                status = "missing"
            elif any(p in val.lower() for p in placeholders):
                status = "placeholder"
            else:
                status = "configured"
            result.append({"key": c["key"], "label": c["label"], "critical": c["critical"], "status": status})
        ok = sum(1 for r in result if r["status"] == "configured")
        critical_missing = sum(1 for r in result if r["critical"] and r["status"] != "configured")
        return {"keys": result, "summary": {"configured": ok, "criticalMissing": critical_missing}}

    def simulate(self, payload: dict) -> dict[str, Any]:
        from app.physics import get_degradation
        twin_id = payload.get("twin_id", "default")
        deg = get_degradation(twin_id)
        uncertainty = payload.get("uncertainty", 0)
        pressure = payload.get("pressure", 0)
        deg.accumulate_stress(uncertainty * 0.1)
        deg.set_cognitive_load(pressure)
        deg.decay_under_pressure(pressure)
        result = self._twin.simulate_behavior(payload)
        result["simulation"] = True
        result["committed"] = False
        result["performance_factor"] = deg.performance_factor
        return result

    def evolve(self, payload: dict) -> dict[str, Any]:
        from app.cortex import (
            auth_class_from_token,
            authority_allows,
            capability_enabled,
            wrap_response,
        )
        from app.physics import (
            consume_evolution_budget,
            replenish_evolution_budget,
            telemetry,
            validate_identity_immutability,
        )
        if not capability_enabled("evolution"):
            return wrap_response({"error": "evolution disabled", "feedback_ingested": False}, ok=False, silence=True)
        auth = auth_class_from_token(payload.get("authToken"))
        if not authority_allows(auth, "evolution"):
            return wrap_response({"error": "orchestrator authority required", "feedback_ingested": False}, ok=False, silence=True)
        if not consume_evolution_budget():
            return wrap_response({"error": "evolution_budget_exhausted", "feedback_ingested": False}, ok=False, silence=True)
        valid, reason = validate_identity_immutability(payload)
        if not valid:
            replenish_evolution_budget(1.0, "rollback_identity")
            telemetry.record_failed_mutation()
            return wrap_response({"error": reason, "feedback_ingested": False}, ok=False, silence=True)
        evolution_mode = payload.get("evolution_mode", "sandbox")
        result = self._twin.evolve(payload)
        result["evolution_mode"] = evolution_mode
        result["committed"] = False
        return result

    # ------------------------------------------------------------------
    # Emotion compute
    # ------------------------------------------------------------------

    async def emotion_compute(self, payload: dict) -> dict[str, Any]:
        from app.physics import fallback_for
        try:
            return await self._emotion.compute(payload)
        except Exception:
            return fallback_for("emotion")

    # ------------------------------------------------------------------
    # Training + eSIM
    # ------------------------------------------------------------------

    async def train_start(self) -> dict[str, Any]:
        from app.physics import replenish_evolution_budget
        from app.runtime import emotion_service as _emo
        from app.runtime import learning_service as _learn
        started = await _learn.train(_emo)
        if started:
            replenish_evolution_budget(2.0, "training_completion")
        return {"started": bool(started)}

    def train_status(self) -> dict[str, Any]:
        from app.runtime import learning_service as _learn
        return _learn.get_status()

    def esim_status(self) -> dict[str, Any]:
        from app.runtime import esim_service as _esim
        return _esim.get_status()  # type: ignore[no-any-return]

    # ------------------------------------------------------------------
    # Speech embodiment
    # ------------------------------------------------------------------

    async def speech_embody(
        self, transcript: str, context: dict | None = None, audience_model: dict | None = None
    ) -> dict[str, Any]:
        import time

        from app.physics import telemetry
        embody, execution_plan = self._speech_em.process(
            transcript, context=context or {}, audience_model=audience_model or {}
        )
        if embody.silence:
            return {
                "response": "",
                "phonemes": [],
                "emotion": embody.emotion,
                "prosody": {"pitch": embody.prosody.pitch, "tempo": embody.prosody.tempo, "intensity": embody.prosody.intensity},
                "audio_base64": None,
                "silence": True,
                "confidence": embody.confidence,
                "execution_plan": execution_plan,
            }
        t0 = time.perf_counter()
        audio_b64 = None
        try:
            import base64

            from app.runtime import voice_broker
            chunks = []
            async for chunk in voice_broker.stream_tts(embody.text[:1000]):
                chunks.append(chunk)
            audio_b64 = base64.b64encode(b"".join(chunks)).decode("ascii")
        except (RuntimeError, Exception):
            pass
        telemetry.record_speech((time.perf_counter() - t0) * 1000)
        phoneme_list = [{"viseme": p.viseme, "start_ms": p.start_ms, "end_ms": p.end_ms} for p in embody.phonemes]
        return {
            "response": embody.text,
            "phonemes": phoneme_list,
            "emotion": embody.emotion,
            "prosody": {"pitch": embody.prosody.pitch, "tempo": embody.prosody.tempo, "intensity": embody.prosody.intensity},
            "audio_base64": audio_b64,
            "silence": False,
            "confidence": embody.confidence,
            "execution_plan": execution_plan,
            "viseme_map": {v: self._speech_em.viseme_to_expression(v) for v in ("AA", "EE", "OH", "FV", "BMP", "TH", "Rest")},
        }

    async def speech_embody_speak(self, text: str) -> dict[str, Any]:
        if not text.strip():
            return {"response": "", "phonemes": [], "audio_base64": None, "viseme_map": {}}
        phonemes = self._speech_em.text_to_phoneme_sequence(text)
        phoneme_list = [{"viseme": p.viseme, "start_ms": p.start_ms, "end_ms": p.end_ms} for p in phonemes]
        audio_b64 = None
        try:
            import base64

            from app.runtime import voice_broker
            chunks = []
            async for chunk in voice_broker.stream_tts(text[:1000]):
                chunks.append(chunk)
            audio_b64 = base64.b64encode(b"".join(chunks)).decode("ascii")
        except (RuntimeError, Exception):
            pass
        return {
            "response": text,
            "phonemes": phoneme_list,
            "emotion": "neutral",
            "audio_base64": audio_b64,
            "viseme_map": {v: self._speech_em.viseme_to_expression(v) for v in ("AA", "EE", "OH", "FV", "BMP", "TH", "Rest")},
        }

    def speech_embodiment_skill(self) -> dict[str, Any]:
        from app.services.speech_embodiment import SKILL_DEFINITION
        return SKILL_DEFINITION

    def speech_embodiment_memory_clear(self) -> dict[str, Any]:
        self._speech_em.clear_memory()
        return {"ok": True}

    def speech_embodiment_memory(self) -> dict[str, Any]:
        return {"history": self._speech_em.get_dialogue_history()}
