"""
Digital Cognitive Twin — BRIDGE AI OS
Models: thinking patterns, decision heuristics, communication style, risk tolerance,
strategic preferences, ethical constraints, learning adaptation loop.

Constraints:
- Avoid hallucination
- Admit uncertainty
- Default to silence if no positive-value output exists
- Optimize for long-term structural advantage
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional

# =============================================================================
# Phase 1 — Identity Mapping
# =============================================================================

class CognitiveMode(str, Enum):
    ANALYTICAL = "analytical"
    INTUITIVE = "intuitive"
    STRATEGIC = "strategic"
    COLLABORATIVE = "collaborative"
    REFLECTIVE = "reflective"


class TimeHorizon(str, Enum):
    SHORT = "short"      # days–weeks
    MID = "mid"          # months–quarters
    LONG = "long"        # years–decades


class ConflictStyle(str, Enum):
    AVOID = "avoid"
    ACCOMMODATE = "accommodate"
    COMPROMISE = "compromise"
    COMPETE = "compete"
    COLLABORATE = "collaborate"


@dataclass
class IdentityMapping:
    core_values: list[str]
    cognitive_mode: CognitiveMode
    time_horizon_bias: TimeHorizon
    conflict_style: ConflictStyle
    pattern_recognition: str  # e.g. "systemic", "analogical", "causal"
    information_compression: str  # e.g. "principles-first", "examples-first", "hierarchical"


# =============================================================================
# Phase 2 — Skill Architecture: Skill = (Hard × Soft) × Meta
# =============================================================================

@dataclass
class SkillStack:
    hard: list[str]   # technical capability
    soft: list[str]   # interpersonal capacity
    meta: list[str]   # learning orchestration, adaptability, reflective loop

    def effective_skill(self) -> float:
        """Skill = (Hard × Soft) × Meta — multiplicative, not additive."""
        h = max(0.01, len(self.hard) / 10.0)
        s = max(0.01, len(self.soft) / 10.0)
        m = max(0.01, len(self.meta) / 5.0)
        return (h * s) * m


# =============================================================================
# Phase 3 — Decision Engine
# =============================================================================

@dataclass
class DecisionInput:
    environment: dict
    goal_vector: list[float]
    constraints: set[str]
    risk_threshold: float


@dataclass
class ActionCandidate:
    action_id: str
    expected_value: float
    ethical_compliance: float
    strategic_alignment: float
    long_term_compounding: float
    rank: float


# =============================================================================
# Phase 4 — Behavioral Simulation
# =============================================================================

@dataclass
class StressScenario:
    uncertainty: float
    pressure: float
    loss: float
    opportunity: float


# =============================================================================
# Phase 5 — Evolution Layer: Recognize → Reorder → Respond → Reflect
# =============================================================================

@dataclass
class EvolutionState:
    recognize: list[str]
    reorder: list[str]
    respond: list[str]
    reflect: list[str]


# =============================================================================
# Twin Profile (Final Output)
# =============================================================================

@dataclass
class TwinProfile:
    identity: IdentityMapping
    skill_stack: SkillStack
    decision_model: dict
    adaptive_loop: EvolutionState
    risk_model: dict
    communication_style: dict
    blind_spots: list[str]
    upgrade_path: list[str]


# =============================================================================
# Default BRIDGE Twin Profile
# =============================================================================

DEFAULT_IDENTITY = IdentityMapping(
    core_values=["integrity", "long-term compounding", "poverty reduction", "lawful execution", "transparency"],
    cognitive_mode=CognitiveMode.STRATEGIC,
    time_horizon_bias=TimeHorizon.LONG,
    conflict_style=ConflictStyle.COLLABORATE,
    pattern_recognition="systemic",
    information_compression="principles-first",
)

DEFAULT_SKILL_STACK = SkillStack(
    hard=["mission_tracking", "api_integration", "state_management", "voice_synthesis", "emotion_compute", "Twin_Speech_Communication_Embodiment", "Bridge_System_Comprehension"],
    soft=["empathic_listening", "clarification", "de_escalation", "stakeholder_alignment"],
    meta=["reflective_loop", "uncertainty_admission", "silence_when_no_value", "learning_orchestration"],
)

DEFAULT_EVOLUTION = EvolutionState(
    recognize=["confidence_below_threshold", "ethical_violation_risk", "strategic_misalignment"],
    reorder=["prioritize_long_term", "defer_until_clarity", "escalate_uncertainty"],
    respond=["structured_response", "admit_uncertainty", "default_silence_if_no_value"],
    reflect=["post_decision_review", "pattern_update", "skill_gap_identification"],
)

DEFAULT_PROFILE = TwinProfile(
    identity=DEFAULT_IDENTITY,
    skill_stack=DEFAULT_SKILL_STACK,
    decision_model={
        "weights": {"expected_value": 0.3, "ethical_compliance": 0.35, "strategic_alignment": 0.2, "long_term_compounding": 0.15},
        "silence_threshold": 0.0,  # no positive-value output → silence
        "uncertainty_admission_threshold": 0.65,
    },
    adaptive_loop=DEFAULT_EVOLUTION,
    risk_model={
        "tolerance": "conservative",
        "max_acceptable_loss": 0.05,
        "prefer_certainty_over_speculation": True,
    },
    communication_style={
        "tone": "authoritative_but_humble",
        "default_to_silence": True,
        "admit_uncertainty": True,
        "avoid_hallucination": True,
    },
    blind_spots=["overconfidence_in_novel_domains", "impatience_under_pressure", "scope_creep_tendency"],
    upgrade_path=["deeper_mission_alignment", "faster_uncertainty_detection", "richer_ethical_lattice"],
)


# =============================================================================
# Cognitive Twin Service
# =============================================================================

class CognitiveTwinService:
    """
    Digital Cognitive Twin — decision engine, behavioral simulation, evolution loop.
    """

    def __init__(self):
        self.profile = DEFAULT_PROFILE

    def get_profile(self) -> dict:
        """Return structured Twin Profile for API/serialization."""
        return {
            "identity": {
                "core_values": self.profile.identity.core_values,
                "cognitive_mode": self.profile.identity.cognitive_mode.value,
                "time_horizon_bias": self.profile.identity.time_horizon_bias.value,
                "conflict_style": self.profile.identity.conflict_style.value,
                "pattern_recognition": self.profile.identity.pattern_recognition,
                "information_compression": self.profile.identity.information_compression,
            },
            "skill_stack": {
                "hard": self.profile.skill_stack.hard,
                "soft": self.profile.skill_stack.soft,
                "meta": self.profile.skill_stack.meta,
                "effective_skill": self.profile.skill_stack.effective_skill(),
            },
            "decision_model": self.profile.decision_model,
            "adaptive_loop": {
                "recognize": self.profile.adaptive_loop.recognize,
                "reorder": self.profile.adaptive_loop.reorder,
                "respond": self.profile.adaptive_loop.respond,
                "reflect": self.profile.adaptive_loop.reflect,
            },
            "risk_model": self.profile.risk_model,
            "communication_style": self.profile.communication_style,
            "blind_spots": self.profile.blind_spots,
            "upgrade_path": self.profile.upgrade_path,
        }

    def decide(
        self,
        environment: dict,
        goal_vector: list[float],
        constraints: set[str],
        risk_threshold: float,
        candidates: list[dict],
    ) -> Optional[dict]:
        """
        Decision function. Ranks action candidates.
        Returns None (silence) if no positive-value output exists.
        """
        weights = self.profile.decision_model.get("weights", {})
        silence_threshold = self.profile.decision_model.get("silence_threshold", 0.0)

        ranked = []
        for c in candidates:
            ev = c.get("expected_value", 0)
            eth = c.get("ethical_compliance", 0)
            strat = c.get("strategic_alignment", 0)
            lt = c.get("long_term_compounding", 0)

            rank = (
                ev * weights.get("expected_value", 0.25)
                + eth * weights.get("ethical_compliance", 0.35)
                + strat * weights.get("strategic_alignment", 0.2)
                + lt * weights.get("long_term_compounding", 0.2)
            )
            if rank > silence_threshold:
                ranked.append({**c, "rank": rank})

        if not ranked:
            return None  # Default to silence

        ranked.sort(key=lambda x: x["rank"], reverse=True)
        return {"action": ranked[0], "alternatives": ranked[1:4]}

    def simulate_behavior(self, scenario: dict) -> dict:
        """Behavioral simulation under stress."""
        uncertainty = scenario.get("uncertainty", 0)
        pressure = scenario.get("pressure", 0)
        loss = scenario.get("loss", 0)
        opportunity = scenario.get("opportunity", 0)

        # Under uncertainty → admit, defer
        if uncertainty > 0.7:
            return {"reaction": "admit_uncertainty", "action": "defer_until_clarity"}

        # Under loss → stabilize, no panic
        if loss > 0.5:
            return {"reaction": "stabilize", "action": "focus_on_mission_alignment"}

        # Under pressure → prioritize ethical compliance
        if pressure > 0.7:
            return {"reaction": "prioritize_ethics", "action": "reorder_constraints"}

        # Under opportunity → verify long-term alignment
        if opportunity > 0.8:
            return {"reaction": "verify_alignment", "action": "assess_compounding_effect"}

        return {"reaction": "proceed", "action": "apply_decision_model"}

    def evolve(self, feedback: dict) -> dict:
        """Evolution loop: Recognize → Reorder → Respond → Reflect."""
        return {
            "recognize": self.profile.adaptive_loop.recognize,
            "reorder": self.profile.adaptive_loop.reorder,
            "respond": self.profile.adaptive_loop.respond,
            "reflect": self.profile.adaptive_loop.reflect,
            "feedback_ingested": True,
        }
