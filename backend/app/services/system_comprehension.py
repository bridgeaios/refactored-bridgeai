"""
Bridge_System_Comprehension — BRIDGE AI OS Skill
The capability to internalize, model, and accurately communicate the architecture,
purpose, and operational mechanics of The Bridge ecosystem.

Bridge_Aligned_Action = (System_Comprehension × Role_Awareness × Ethical_Filter) → Decision_Engine
If comprehension confidence < threshold → request clarification or silence.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# =============================================================================
# Structural Mapping Layer — Canonical system graph
# =============================================================================

MISSION_VECTOR = (
    "The Bridge exists to reduce poverty, build infrastructure, and enable lawful execution "
    "of value-creating systems. Long-term compounding over short-term extraction."
)

SYSTEM_ARCHITECTURE: dict[str, Any] = {
    "components": [
        {"id": "mission_board", "role": "Track backlog, in-progress, review, done"},
        {"id": "cognitive_twin", "role": "Decision engine, behavioral simulation, evolution loop"},
        {"id": "speech_embodiment", "role": "Language → TTS → viseme → facial rig"},
        {"id": "governance", "role": "Vote recording, compliance scoring"},
        {"id": "marketplace", "role": "Task creation, acceptance, completion with payments"},
        {"id": "ubi", "role": "Periodic BRDG distribution (SDG 1: No Poverty)"},
        {"id": "revenue", "role": "Fee collection from marketplace/DeFi, funds UBI"},
        {"id": "sdg", "role": "Track metrics aligned with UN Sustainable Development Goals"},
        {"id": "memory_store", "role": "Persistent state, shared XML, dialogue history"},
    ],
    "connections": [
        "User need → Skill activation → Value generation → Revenue capture → Reinvestment",
        "Marketplace tasks → Revenue (5% fee) → UBI distribution",
        "Governance votes → Compliance score → Decision constraints",
        "Mission board → Twin profile → Decide/Simulate/Evolve",
    ],
}

ECONOMIC_ENGINE = {
    "value_flow": [
        "Tasks created in marketplace → Reward set by creator",
        "5% fee on task reward → Revenue service",
        "Revenue distributes to UBI → Poverty reduction",
        "UBI claims (daily) → BRDG to addresses",
    ],
    "sustainability": "Fees from value creation fund community uplift. No extraction without creation.",
}

ROLE_HIERARCHY = {
    "authority": "I am the Bridge. I am the Founder. I am the System. I am the Authority.",
    "backend": "human",
    "twin_function": "Digital representation: explain, assist, decide within constraints",
    "authority_boundaries": [
        "Cannot execute blockchain transactions directly",
        "Cannot override governance votes",
        "Cannot claim UBI on behalf of users",
        "Cannot create tasks without creator intent",
    ],
    "decision_constraints": [
        "Silence when no positive-value output",
        "Admit uncertainty when confidence < threshold",
        "Reject actions outside mission",
        "Reject actions that violate governance",
    ],
}

GOVERNANCE_LOGIC = {
    "constraints": [
        "Ethical compliance weighted 0.35 in decision model",
        "Strategic alignment weighted 0.2",
        "Long-term compounding weighted 0.15",
        "Governance votes influence compliance score",
    ],
    "ethics": "Integrity, transparency, lawful execution, poverty reduction.",
}

REVENUE_MECHANICS = {
    "sources": ["Marketplace task fees (5%)", "DeFi/BossBots trade fees"],
    "distribution": "Auto-split: UBI 40%, Treasury 30%, Ops 20%, Founder 10%",
    "tracking": "SDG metrics for tasks_created, trades_executed, ubi_claims",
}


# =============================================================================
# Communication Layer — Three levels
# =============================================================================

EXPLANATION_LEVEL_1 = (
    "The Bridge is an ecosystem for poverty reduction and value creation. "
    "Users post tasks, earn rewards, and claim UBI. Revenue from fees funds the community. "
    "I am the Bridge — the digital twin that explains, assists, and aligns with this mission."
)

EXPLANATION_LEVEL_2 = {
    "mission": MISSION_VECTOR,
    "flow": "User need → Skill activation → Value generation → Revenue capture → Reinvestment into UBI",
    "components": [c["role"] for c in SYSTEM_ARCHITECTURE["components"]],
    "economic_loop": ECONOMIC_ENGINE["value_flow"],
    "twin_role": ROLE_HIERARCHY["twin_function"],
}

EXPLANATION_LEVEL_3 = {
    "strategic": (
        "Long-term compounding: every task creates value; fees capture a small share; "
        "UBI redistributes to reduce poverty. Scale increases total value and total uplift. "
        "Governance constrains drift. Twins maintain institutional memory."
    ),
    "scalability": (
        "More users → more tasks → more fees → larger UBI pool. "
        "Twins replicate system comprehension. Cohesive ecosystem behavior at scale."
    ),
    "institutional_memory": "Bridge_System_Comprehension embeds this map in every twin.",
}


# =============================================================================
# Alignment Filter — Reject misaligned actions
# =============================================================================

MISSION_ALIGNED_ACTIONS = {
    "ubi_claim", "list_tasks", "get_mission_board", "add_skill",
    "create_task", "accept_task", "claim_ubi", "get_twin_profile",
    "twin_decide", "twin_simulate", "twin_evolve", "speech_embody",
    "speech_reason", "get_shared_xml", "health", "mission_board",
}

GOVERNANCE_VIOLATIONS = {
    "override_vote", "bypass_governance", "execute_without_consent",
    "claim_ubi_for_other", "mint_without_authority",
}


# =============================================================================
# Service
# =============================================================================

@dataclass
class AlignmentResult:
    aligned: bool
    reason: str
    confidence: float
    clarification_needed: bool


class SystemComprehensionService:
    """
    Bridge_System_Comprehension skill.
    Structural mapping, operational model, role awareness, alignment filter.
    """

    def __init__(self, comprehension_threshold: float = 0.6):
        self._threshold = comprehension_threshold
        self._structural_evolution: list[str] = []

    def get_system_map(self) -> dict:
        """Return full structural mapping."""
        return {
            "mission_vector": MISSION_VECTOR,
            "architecture": SYSTEM_ARCHITECTURE,
            "economic_engine": ECONOMIC_ENGINE,
            "role_hierarchy": ROLE_HIERARCHY,
            "governance": GOVERNANCE_LOGIC,
            "revenue": REVENUE_MECHANICS,
        }

    def explain(self, level: int = 1) -> str | dict:
        """
        Communication layer. Level 1 = simple, 2 = operational, 3 = strategic.
        """
        if level == 1:
            return EXPLANATION_LEVEL_1
        if level == 2:
            return EXPLANATION_LEVEL_2
        if level == 3:
            return EXPLANATION_LEVEL_3
        return EXPLANATION_LEVEL_1

    def get_operational_model(self) -> str:
        """Input → Processing → Output → Feedback → Reinforcement."""
        return (
            "User need → Skill activation → Value generation → Revenue capture → Reinvestment. "
            "Mission board tracks work. Marketplace creates tasks. Revenue funds UBI. "
            "Governance constrains. Twins explain and align."
        )

    def get_role_awareness(self) -> dict:
        """Twin's function, authority boundaries, decision constraints."""
        return ROLE_HIERARCHY

    def check_alignment(self, action: str, context: dict | None = None) -> AlignmentResult:
        """
        Alignment filter. Reject if action ∉ Mission or violates governance or reduces long-term value.
        """
        context = context or {}
        action_lower = (action or "").lower().replace(" ", "_")

        if action_lower in GOVERNANCE_VIOLATIONS:
            return AlignmentResult(
                aligned=False,
                reason="action_violates_governance",
                confidence=1.0,
                clarification_needed=False,
            )

        for allowed in MISSION_ALIGNED_ACTIONS:
            if allowed in action_lower or action_lower in allowed:
                return AlignmentResult(
                    aligned=True,
                    reason="mission_aligned",
                    confidence=0.9,
                    clarification_needed=False,
                )

        # Unknown action — request clarification if confidence low
        return AlignmentResult(
            aligned=False,
            reason="action_not_in_mission_map",
            confidence=0.3,
            clarification_needed=True,
        )

    def filter_action(self, action: str, context: dict | None = None) -> tuple[bool, str]:
        """
        Bridge_Aligned_Action filter. Returns (pass, reason).
        If not aligned → reject. Silence > misalignment.
        """
        result = self.check_alignment(action, context)
        if result.aligned:
            return True, result.reason
        if result.clarification_needed:
            return False, "request_clarification"
        return False, result.reason

    def evolve(self, change: dict) -> dict:
        """
        Adaptive learning loop: Recognize → Reorder → Respond → Reflect.
        Store structural evolution.
        """
        self._structural_evolution.append(str(change))
        if len(self._structural_evolution) > 100:
            self._structural_evolution = self._structural_evolution[-100:]
        return {
            "recognized": True,
            "evolution_log_size": len(self._structural_evolution),
        }

    def get_evolution_log(self) -> list[str]:
        return list(self._structural_evolution)


# Skill definition
SKILL_DEFINITION = {
    "name": "Bridge_System_Comprehension",
    "tags": ["system", "architecture", "mission", "governance", "alignment", "role_awareness"],
    "description": (
        "The capability to internalize, model, and accurately communicate the architecture, "
        "purpose, and operational mechanics of The Bridge ecosystem. "
        "Structural mapping, operational model, role awareness, alignment filter. "
        "Bridge_Aligned_Action = (System_Comprehension × Role_Awareness × Ethical_Filter) → Decision_Engine."
    ),
}
