"""
Twin_Speech_Communication_Embodiment — BRIDGE AI OS Skill Module
Drop-in: Language Engine → TTS → Phoneme Stream → Viseme Driver → Facial Rig.
Functional speech embodiment. Not cosmetic chatter.
"""
from __future__ import annotations

import re
import asyncio
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

# Lazy import to avoid circular deps
def _get_system_comprehension():
    from app.services.system_comprehension import SystemComprehensionService
    return SystemComprehensionService()

# Viseme set (Oculus/MetaHuman compatible)
VISEMES = ("AA", "EE", "OH", "FV", "BMP", "TH", "Rest")

# ARPAbet/IPA → Viseme mapping
PHONEME_TO_VISEME = {
    "AA": "AA", "AE": "AA", "AH": "AA", "AO": "OH", "AW": "OH", "AY": "AA",
    "EH": "EE", "ER": "OH", "EY": "EE",
    "IH": "EE", "IY": "EE",
    "OW": "OH", "OY": "OH",
    "UH": "OH", "UW": "OH",
    "B": "BMP", "P": "BMP", "M": "BMP",
    "F": "FV", "V": "FV",
    "TH": "TH", "DH": "TH",
    "D": "Rest", "T": "Rest", "N": "Rest", "L": "Rest", "R": "Rest",
    "S": "Rest", "Z": "Rest", "SH": "Rest", "ZH": "Rest", "CH": "Rest", "JH": "Rest",
    "K": "Rest", "G": "Rest", "NG": "Rest",
    "W": "OH", "Y": "EE", "HH": "Rest", "AX": "AA", "AXR": "OH",
}

# Grapheme → phoneme approximation (simplified)
def _grapheme_to_phoneme(word: str) -> list[str]:
    """Simple rule-based G2P. Returns list of phoneme strings."""
    word = word.lower().strip()
    if not word:
        return []
    out = []
    i = 0
    while i < len(word):
        c = word[i]
        # Vowels
        if c in "aeiou":
            if i + 1 < len(word):
                n = word[i + 1]
                if c == "a" and n in "iou":
                    out.append("AE" if n == "e" else "AA")
                    i += 2
                    continue
                if c == "e" and n == "e":
                    out.append("IY")
                    i += 2
                    continue
                if c == "o" and n == "o":
                    out.append("UW")
                    i += 2
                    continue
                if c == "o" and n == "u":
                    out.append("AW")
                    i += 2
                    continue
            out.append({"a": "AA", "e": "EH", "i": "IH", "o": "AO", "u": "UH"}.get(c, "AA"))
        elif c == "y" and (i == 0 or word[i - 1] not in "aeiou"):
            out.append("Y")
        elif c in "bp":
            out.append("BMP")
        elif c in "fv":
            out.append("FV")
        elif c == "m":
            out.append("BMP")
        elif c == "t" and i + 1 < len(word) and word[i + 1] == "h":
            out.append("TH")
            i += 2
            continue
        elif c == "s" and i + 1 < len(word) and word[i + 1] == "h":
            out.append("SH")
            i += 2
            continue
        elif c in "tdnlrszckg":
            out.append("Rest")
        elif c == "w":
            out.append("W")
        elif c == "h":
            out.append("HH")
        elif c in "j":
            out.append("JH")
        else:
            out.append("Rest")
        i += 1
    return out


@dataclass
class PhonemeSegment:
    phoneme: str
    viseme: str
    start_ms: float
    end_ms: float


@dataclass
class ProsodyParams:
    pitch: float  # 0.8–1.2
    tempo: float  # 0.85–1.15
    intensity: float  # 0.8–1.2


@dataclass
class EmbodyOutput:
    text: str
    emotion: str
    prosody: ProsodyParams
    phonemes: list[PhonemeSegment]
    confidence: float
    silence: bool  # True if semantic confidence < threshold


# Emotional modulation: voice + face
EMOTION_TO_PROSDY = {
    "neutral": ProsodyParams(1.0, 1.0, 1.0),
    "positive": ProsodyParams(1.05, 1.05, 1.1),
    "negative": ProsodyParams(0.95, 0.9, 0.9),
    "urgent": ProsodyParams(1.1, 1.2, 1.15),
    "reflective": ProsodyParams(0.92, 0.88, 0.95),
    "focused": ProsodyParams(1.0, 1.02, 1.0),
}


class SpeechEmbodimentService:
    """
    Twin_Speech_Communication_Embodiment skill.
    Communication_Output = (Language_Model_Response × Emotional_Modulation × Audience_Model)
    → TTS → Phoneme_Stream → Viseme_Driver → Facial_Rig
    """

    def __init__(self, memory_size: int = 20):
        self._memory: deque[dict] = deque(maxlen=memory_size)
        self._silence_threshold = 0.0  # No positive-value output → silence

    def _get_language_engine(self):
        from app.services.speech_reasoning import SpeechReasoningService
        return SpeechReasoningService()

    def text_to_phoneme_sequence(self, text: str, words_per_sec: float = 2.5) -> list[PhonemeSegment]:
        """
        Convert text to time-aligned phoneme sequence.
        words_per_sec: approximate speech rate for duration estimation.
        """
        words = re.findall(r"\b\w+\b", text)
        if not words:
            return [PhonemeSegment("Rest", "Rest", 0.0, 0.3)]

        total_duration_ms = len(words) * (1000.0 / words_per_sec)
        ms_per_word = total_duration_ms / len(words)
        segments = []
        t = 0.0

        for word in words:
            phonemes = _grapheme_to_phoneme(word)
            if not phonemes:
                phonemes = ["Rest"]
            dur_per_phoneme = ms_per_word / len(phonemes)
            for p in phonemes:
                viseme = PHONEME_TO_VISEME.get(p, "Rest")
                if viseme not in VISEMES:
                    viseme = "Rest"
                segments.append(PhonemeSegment(p, viseme, t, t + dur_per_phoneme))
                t += dur_per_phoneme

        # Ensure Rest at end
        if segments and segments[-1].viseme != "Rest":
            segments.append(PhonemeSegment("Rest", "Rest", t, t + 0.15))
        return segments

    def viseme_to_expression(self, viseme: str) -> dict:
        """
        Map viseme to facial expression params for our rig.
        jawOpen, smile, frown — compatible with setExpression.
        """
        v = viseme or "Rest"
        # AA: open jaw; EE: smile, tight lips; OH: round, mid jaw; FV: lip protrusion; BMP: closed; TH: teeth; Rest: neutral
        map_ = {
            "AA": {"jawOpen": 0.45, "smile": 0.1, "frown": 0},
            "EE": {"jawOpen": 0.08, "smile": 0.7, "frown": 0},
            "OH": {"jawOpen": 0.35, "smile": 0.05, "frown": 0},
            "FV": {"jawOpen": 0.12, "smile": 0.25, "frown": 0.08},
            "BMP": {"jawOpen": 0.02, "smile": 0.1, "frown": 0},
            "TH": {"jawOpen": 0.18, "smile": 0.15, "frown": 0.05},
            "Rest": {"jawOpen": 0.04, "smile": 0.2, "frown": 0},
        }
        return map_.get(v, map_["Rest"])

    def process(
        self,
        transcript_or_prompt: str,
        context: Optional[dict] = None,
        audience_model: Optional[dict] = None,
    ) -> tuple[EmbodyOutput, Optional[dict]]:
        """
        Full pipeline: Language Engine → Emotional Modulation → Phoneme Sequence.
        Returns (EmbodyOutput, execution_plan or None).
        If semantic confidence < threshold → silence.
        """
        engine = self._get_language_engine()
        context = context or {}
        context["dialogue_history"] = list(self._memory)

        result = engine.process(transcript_or_prompt, context=context)
        out_dict = engine.to_dict(result)

        # Semantic confidence check
        confidence = result.confidence
        if confidence < self._silence_threshold or not result.response:
            self._memory.append({"role": "user", "text": transcript_or_prompt})
            self._memory.append({"role": "assistant", "text": "", "silence": True})
            return (
                EmbodyOutput(
                    text="",
                    emotion=result.emotion,
                    prosody=EMOTION_TO_PROSDY.get(result.emotion, EMOTION_TO_PROSDY["neutral"]),
                    phonemes=[],
                    confidence=confidence,
                    silence=True,
                ),
                None,
            )

        # Emotional modulation
        emotion = result.emotion
        if result.urgency == "high":
            emotion = "urgent"
        prosody = EMOTION_TO_PROSDY.get(emotion, EMOTION_TO_PROSDY["neutral"])
        tempo = prosody.tempo
        words_per_sec = 2.5 * tempo

        # Alignment filter (Bridge_System_Comprehension)
        execution_plan = result.execution_plan
        response_text = result.response
        if execution_plan:
            action = execution_plan.get("action", "")
            sys_comp = _get_system_comprehension()
            aligned, reason = sys_comp.filter_action(action, context)
            if not aligned:
                execution_plan = None
                if reason == "request_clarification":
                    response_text = "I need to clarify — that action may be outside my mission scope. Could you rephrase?"

        # Phoneme sequence
        phonemes = self.text_to_phoneme_sequence(response_text, words_per_sec=words_per_sec)

        # Update memory
        self._memory.append({"role": "user", "text": transcript_or_prompt})
        self._memory.append({"role": "assistant", "text": response_text, "intent": result.intent})

        return (
            EmbodyOutput(
                text=response_text,
                emotion=emotion,
                prosody=prosody,
                phonemes=phonemes,
                confidence=confidence,
                silence=False,
            ),
            execution_plan,
        )

    def get_dialogue_history(self) -> list[dict]:
        return list(self._memory)

    def clear_memory(self) -> None:
        self._memory.clear()


# Skill definition for mission board
SKILL_DEFINITION = {
    "name": "Twin_Speech_Communication_Embodiment",
    "tags": ["speech", "tts", "lip_sync", "viseme", "conversation", "embodiment"],
    "description": (
        "Enables the twin to generate structured language, convert to natural speech, "
        "synchronize facial articulation, and adapt communication dynamically. "
        "Language Engine → TTS → Phoneme Stream → Viseme Driver → Facial Rig."
    ),
}
