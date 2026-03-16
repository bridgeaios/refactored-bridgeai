"""
Speech Communication Reasoning Layer — BRIDGE AI OS
Never let raw speech directly trigger execution. This is the buffer.
"""
import re
from dataclasses import dataclass
from typing import Optional

# Filler patterns (case-insensitive, whole-word)
FILLER_PATTERN = re.compile(
    r"\b(um|uh|hmm|er|ah|like|you\s+know|sort\s+of|kind\s+of|basically|actually|literally|i\s+mean)\b",
    re.IGNORECASE
)

# Intent keywords (operational, philosophical, emotional, inquiry, command)
INTENT_SIGNALS = {
    "command": [
        "do", "run", "execute", "start", "stop", "show", "display", "open", "close",
        "create", "delete", "add", "remove", "claim", "accept", "submit", "send"
    ],
    "inquiry": [
        "what", "when", "where", "why", "how", "who", "which", "tell me", "explain",
        "describe", "can you", "could you", "would you", "is there", "are there"
    ],
    "philosophical": [
        "meaning", "purpose", "believe", "think", "why do we", "should we", "ought",
        "right", "wrong", "ethics", "moral", "philosophy"
    ],
    "emotional": [
        "feel", "frustrated", "angry", "sad", "happy", "worried", "scared", "love",
        "hate", "upset", "annoyed", "excited", "stressed", "anxious"
    ],
    "greeting": ["hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening"],
    "identity": ["who are you", "about yourself", "what are you", "introduce yourself"],
    "help": ["help", "assist", "support", "guide", "what can you do", "capabilities"],
    "system": ["how does the bridge work", "explain the system", "architecture", "how does it work", "what is the bridge", "mission", "economic", "revenue", "ubi flow", "governance"],
}

EMOTION_SIGNALS = {
    "urgent": ["urgent", "asap", "now", "quick", "emergency", "immediately", "critical"],
    "neutral": [],
    "positive": ["thanks", "thank you", "great", "good", "awesome", "love", "appreciate"],
    "negative": ["no", "wrong", "bad", "hate", "terrible", "frustrated", "angry", "upset"],
}

CLARIFICATION_THRESHOLD = 0.65

# Display labels for chat interface — link intent to user-facing topic
INTENT_TO_TOPIC = {
    "command": "Commands",
    "inquiry": "Questions",
    "philosophical": "Philosophy",
    "emotional": "Emotional",
    "greeting": "Greeting",
    "identity": "Identity",
    "help": "Help",
    "system": "System",
    "conversational": "General",
}


@dataclass
class ReasoningResult:
    normalized_text: str
    intent: str
    topic: str
    emotion: str
    urgency: str
    confidence: float
    clarification_needed: bool
    response: str
    execution_plan: Optional[dict] = None


class SpeechReasoningService:
    """
    Reasoning buffer layer. Accepts ASR transcript, normalizes, detects intent/emotion,
    scores confidence, and produces validated response.
    """

    def process(self, raw_transcript: str, context: Optional[dict] = None) -> ReasoningResult:
        """
        Full pipeline: normalize → detect → validate → score → respond.
        """
        context = context or {}
        text = (raw_transcript or "").strip()

        # 1. Normalize
        normalized = self._normalize(text)

        # 2. Detect intent, emotion, urgency
        intent = self._detect_intent(normalized)
        emotion, urgency = self._detect_emotion_urgency(normalized)

        # 3. Compute confidence
        confidence = self._compute_confidence(normalized, intent, emotion)
        clarification_needed = confidence < CLARIFICATION_THRESHOLD

        # 4. Generate response (or clarification)
        if clarification_needed:
            response = self._clarification_response(normalized, confidence)
            execution_plan = None
        else:
            response, execution_plan = self._generate_response(
                normalized, intent, emotion, urgency, context
            )

        topic = INTENT_TO_TOPIC.get(intent, intent.title())
        return ReasoningResult(
            normalized_text=normalized,
            intent=intent,
            topic=topic,
            emotion=emotion,
            urgency=urgency,
            confidence=round(confidence, 3),
            clarification_needed=clarification_needed,
            response=response,
            execution_plan=execution_plan,
        )

    def _normalize(self, text: str) -> str:
        """Remove fillers, fix spacing, capitalize sentences."""
        if not text:
            return ""
        # Remove fillers
        text = FILLER_PATTERN.sub("", text)
        # Collapse whitespace and strip
        text = " ".join(text.split())
        # Basic sentence capitalization
        if text and text[0].islower():
            text = text[0].upper() + text[1:]
        return text.strip()

    def _detect_intent(self, text: str) -> str:
        """Infer intent from normalized text."""
        lower = text.lower()
        scores = {}
        for intent, keywords in INTENT_SIGNALS.items():
            hits = sum(1 for k in keywords if k in lower)
            if hits > 0:
                scores[intent] = hits
        if scores:
            return max(scores, key=lambda k: scores[k])
        # Default: conversational statement
        return "conversational"

    def _detect_emotion_urgency(self, text: str) -> tuple[str, str]:
        """Return (emotion, urgency)."""
        lower = text.lower()
        urgency = "normal"
        for u in EMOTION_SIGNALS["urgent"]:
            if u in lower:
                urgency = "high"
                break
        emotion = "neutral"
        for e in ["negative", "positive"]:
            for s in EMOTION_SIGNALS[e]:
                if s in lower:
                    emotion = "positive" if e == "positive" else "negative"
                    break
        return emotion, urgency

    def _compute_confidence(self, text: str, intent: str, emotion: str) -> float:
        """
        Heuristic confidence: length, intent clarity, coherence.
        Can be replaced with model-based scoring.
        """
        base = 0.7
        if len(text) < 3:
            base -= 0.3
        elif len(text) < 10:
            base -= 0.1
        if intent in ("command", "inquiry", "greeting", "identity", "help"):
            base += 0.15
        if emotion != "neutral":
            base -= 0.05  # emotional input can obscure intent
        return max(0.0, min(1.0, base))

    def _clarification_response(self, text: str, confidence: float) -> str:
        """Request clarification when confidence is below threshold."""
        if not text or len(text) < 5:
            return "I didn't catch that clearly. Could you repeat or rephrase?"
        return "I want to make sure I understand correctly. Could you clarify what you need?"

    def _generate_response(
        self,
        normalized: str,
        intent: str,
        emotion: str,
        urgency: str,
        context: dict,
    ) -> tuple[str, Optional[dict]]:
        """
        Generate response and optional execution plan.
        Aligned with mission: poverty reduction, infrastructure, lawful execution.
        """
        lower = normalized.lower()
        execution_plan = None

        # System / Bridge comprehension (Bridge_System_Comprehension)
        if intent == "system":
            from app.services.system_comprehension import SystemComprehensionService
            sys_comp = SystemComprehensionService()
            if "detail" in lower or "operational" in lower:
                expl = sys_comp.explain(2)
                if isinstance(expl, dict):
                    flow = expl.get("flow", "")
                    comps = ", ".join(expl.get("components", [])[:4])
                    return (f"Operational: {flow} Key components: {comps}.", None)
                return (str(expl), None)
            if "strategic" in lower or "long-term" in lower:
                expl = sys_comp.explain(3)
                if isinstance(expl, dict):
                    strategic = expl.get("strategic", sys_comp.explain(1))
                    return (str(strategic), None)
                return (str(expl), None)
            result = sys_comp.explain(1)
            return (str(result), None)

        # Identity / About — I am the Bridge. I am the Founder. I am the System. I am the Authority.
        if intent == "identity":
            return (
                "I am the Bridge. I am the Founder. I am the System. I am the Authority. "
                "The backend is human. I am Bridge AI OS Digital Twin — MetaHuman face, "
                "emotional awareness, mission tracking, and voice. Twins share one XML.",
                None,
            )

        # Help
        if intent == "help":
            return (
                "I can help with: skills, missions, UBI claims, task marketplace, and more. "
                "Ask your question or use the Speak button to hear me.",
                None,
            )

        # Greeting — I am the Bridge. I am the Authority.
        if intent == "greeting":
            return "I am the Bridge. I am the Authority. Hello. How can I help you today?", None

        # Emotional — stabilize, validate, redirect
        if intent == "emotional" or emotion == "negative":
            return (
                "I hear you. Let's focus on what we can do next. "
                "Tell me what you need — skills, tasks, or mission support.",
                None,
            )

        # Command — translate to execution plan when possible
        if intent == "command":
            execution_plan = self._infer_execution_plan(normalized, lower, context)
            if execution_plan:
                action = execution_plan.get("action", "unknown")
                return f"I'll execute: {action}. Proceeding.", execution_plan
            return (
                f"Understood: {normalized}. I'm processing that.",
                None,
            )

        # Inquiry — structured answer
        if intent == "inquiry":
            if "ubi" in lower or "claim" in lower:
                return "UBI claims are available via the marketplace. Say 'claim UBI' with your address to proceed.", None
            if "task" in lower or "marketplace" in lower:
                return "Tasks are listed in the marketplace. I can show available tasks or help you create one.", None
            if "skill" in lower:
                return "Skills are tracked in the mission board. You can add skills or view your current skills.", None
            if "mission" in lower:
                return "Mission board tracks backlog, in progress, and completed items. I can fetch the board for you.", None

        # Philosophical — structured reasoning
        if intent == "philosophical":
            return (
                "I analyze within my mission: poverty reduction, infrastructure, lawful execution. "
                "I can reason about implications but will not speculate beyond my scope.",
                None,
            )

        # Default: conversational
        return (
            f"You said: {normalized}. I'm Bridge AI OS. "
            "Try 'tell me about yourself', 'help', or ask about UBI, tasks, or missions.",
            None,
        )

    def _infer_execution_plan(self, normalized: str, lower: str, context: dict) -> Optional[dict]:
        """Map command phrases to structured execution plan."""
        if "claim" in lower and ("ubi" in lower or "basic" in lower):
            return {"action": "ubi_claim", "params": {"source": "speech"}, "validated": True}
        if "show" in lower or "display" in lower:
            if "task" in lower:
                return {"action": "list_tasks", "params": {}, "validated": True}
            if "mission" in lower or "board" in lower:
                return {"action": "get_mission_board", "params": {}, "validated": True}
        if "add" in lower and "skill" in lower:
            return {"action": "add_skill", "params": {"from_speech": True}, "validated": False}
        return None

    def to_dict(self, result: ReasoningResult) -> dict:
        """Serialize for WebSocket/API output."""
        return {
            "normalized_text": result.normalized_text,
            "intent": result.intent,
            "topic": result.topic,
            "emotion": result.emotion,
            "urgency": result.urgency,
            "confidence": result.confidence,
            "clarification_needed": result.clarification_needed,
            "response": result.response,
            "execution_plan": result.execution_plan,
        }
