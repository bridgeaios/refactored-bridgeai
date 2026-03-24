"""
Bridge Physics — Governance, Resilience, Scaling

System physics: determinism, silence discipline, central mutation, versioning,
observability, risk ceilings, immutable identity, graceful failure.

Without these, evolution becomes folklore.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field

# =============================================================================
# 1. Determinism Layer — Same inputs + state → same output. Auditability.
# =============================================================================

DETERMINISTIC_MODE = os.environ.get("BRIDGE_DETERMINISTIC", "0") == "1"


def deterministic_seed(inputs: dict, state_version: int = 0) -> int:
    """Stable seed for reproducible decisions. Same inputs + state → same output."""
    canonical = json.dumps(inputs, sort_keys=True) + f"|v{state_version}"
    return int(hashlib.sha256(canonical.encode()).hexdigest()[:16], 16)


# =============================================================================
# 2. Internal Event Bus — Endpoint → Event → Reducer → State → Subscribers
# Backpressure: biology solves with decay and refractory periods.
# =============================================================================

EVENT_QUEUE_MAX = int(os.environ.get("BRIDGE_EVENT_QUEUE_MAX", "100"))
EVENT_DROP_POLICY = os.environ.get("BRIDGE_EVENT_DROP_POLICY", "oldest")  # oldest | newest | block

_subscribers: dict[str, list[Callable]] = {
    "speech": [],
    "emotion": [],
    "economy": [],
    "training": [],
    "state_mutation": [],
    "system_drift": [],
}
_event_queues: dict[str, deque] = {}
for k in _subscribers:
    _event_queues[k] = deque(maxlen=EVENT_QUEUE_MAX)
_event_backlog_depth: dict[str, int] = dict.fromkeys(_subscribers, 0)


def subscribe(channel: str, handler: Callable) -> None:
    _subscribers.setdefault(channel, []).append(handler)


def _dispatch_event(channel: str, event: dict) -> None:
    for h in _subscribers.get(channel, []):
        try:
            h(event)
        except Exception:
            pass


def emit(channel: str, event: dict) -> None:
    """Emit with backpressure. Max queue size, drop policy. Nervous system must not bottleneck."""
    q = _event_queues.get(channel)
    if q is None:
        _event_queues[channel] = deque(maxlen=EVENT_QUEUE_MAX)
        q = _event_queues[channel]
    if len(q) >= EVENT_QUEUE_MAX:
        if EVENT_DROP_POLICY == "oldest":
            q.popleft()
        elif EVENT_DROP_POLICY == "newest":
            return
    q.append(event)
    _event_backlog_depth[channel] = len(q)
    while q:
        ev = q.popleft()
        _event_backlog_depth[channel] = len(q)
        _dispatch_event(channel, ev)


def event_backlog_depth(channel: str | None = None) -> int | dict[str, int]:
    """Telemetry: event_backlog_depth per channel."""
    if channel:
        return _event_backlog_depth.get(channel, 0)
    return dict(_event_backlog_depth)


# =============================================================================
# 3. Failure Modes — Graceful degradation. Systems fail gradually, not catastrophically.
# =============================================================================

DEGRADATION_LEVEL_FULL = 0
DEGRADATION_LEVEL_PARTIAL = 1   # no audio
DEGRADATION_LEVEL_MINIMAL = 2   # text only
DEGRADATION_LEVEL_SILENT = 3

_current_degradation_level: int = DEGRADATION_LEVEL_FULL


def get_degradation_level() -> int:
    """Current system degradation. 0=full, 1=partial, 2=minimal, 3=silent."""
    return _current_degradation_level


def set_degradation_level(level: int) -> None:
    global _current_degradation_level
    _current_degradation_level = max(0, min(3, level))


FAILURE_FALLBACKS: dict[str, dict] = {
    "tts": {"phonemes_only": True, "audio_base64": None},
    "emotion": {"state": "neutral", "score": 0.0},
    "state_mutation_rejected": {"ok": False, "silence": True},
    "marketplace_unavailable": {"tasks": [], "error": "degraded"},
}


def fallback_for(failure_mode: str) -> dict:
    return FAILURE_FALLBACKS.get(failure_mode, {}).copy()


# =============================================================================
# 4. Observability — Measure drift. Without telemetry, blind.
# =============================================================================

@dataclass
class Telemetry:
    decision_latency_ms: deque = field(default_factory=lambda: deque(maxlen=1000))
    speech_latency_ms: deque = field(default_factory=lambda: deque(maxlen=1000))
    silence_count: int = 0
    action_count: int = 0
    state_mutation_count: int = 0
    economic_conversion_count: int = 0
    failed_mutation_count: int = 0
    silence_by_endpoint: dict = field(default_factory=dict)

    def record_decision(self, ms: float) -> None:
        self.decision_latency_ms.append(ms)

    def record_decision_with_seed(self, seed: int, state_version: int) -> None:
        """Log seed + state_version per decision. Determinism with replay is science."""
        self._last_decision_seed = seed
        self._last_decision_state_version = state_version

    def record_speech(self, ms: float) -> None:
        self.speech_latency_ms.append(ms)

    def record_silence(self, endpoint: str = "global") -> None:
        self.silence_count += 1
        self.silence_by_endpoint[endpoint] = self.silence_by_endpoint.get(endpoint, 0) + 1

    def record_action(self) -> None:
        self.action_count += 1

    def record_state_mutation(self) -> None:
        self.state_mutation_count += 1

    def record_failed_mutation(self) -> None:
        self.failed_mutation_count += 1

    def record_economic_conversion(self) -> None:
        self.economic_conversion_count += 1

    @property
    def silence_rate(self) -> float:
        total = self.silence_count + self.action_count
        return self.silence_count / total if total > 0 else 0.0

    @property
    def system_entropy_score(self) -> float:
        """
        Organisms decay. Entropy from: reducer frequency, failed mutations,
        silence rate imbalance, economic volatility.
        0 = low entropy, 1 = high entropy. Scheduler can trigger training/optimization.
        """
        total_mutations = self.state_mutation_count + self.failed_mutation_count
        fail_rate = self.failed_mutation_count / total_mutations if total_mutations > 0 else 0
        silence_imbalance = abs(self.silence_rate - 0.5) * 2  # 0 at 50%, 1 at 0% or 100%
        return min(1.0, fail_rate * 0.4 + silence_imbalance * 0.3 + (1.0 / (1 + self.state_mutation_count)) * 0.3)

    def to_dict(self) -> dict:
        dl = list(self.decision_latency_ms)
        sl = list(self.speech_latency_ms)
        return {
            "decision_latency_p50_ms": sorted(dl)[len(dl) // 2] if dl else 0,
            "decision_latency_p95_ms": sorted(dl)[int(len(dl) * 0.95)] if dl else 0,
            "speech_latency_p50_ms": sorted(sl)[len(sl) // 2] if sl else 0,
            "silence_rate": self.silence_rate,
            "silence_rate_global": self.silence_rate,
            "silence_rate_per_endpoint": dict(self.silence_by_endpoint),
            "state_mutation_frequency": self.state_mutation_count,
            "economic_conversion_rate": self.economic_conversion_count,
            "system_entropy_score": self.system_entropy_score,
            "evolution_budget_remaining": evolution_budget_remaining(),
            "degradation_level": get_degradation_level(),
            "event_backlog_depth": event_backlog_depth(),
            "baseline_drift": get_baseline_drift(),
        }


telemetry = Telemetry()


# =============================================================================
# 4b. Baseline Drift Detection — Telemetry without interpretation is just numbers.
# =============================================================================

BASELINE_SILENCE_RATE = float(os.environ.get("BRIDGE_BASELINE_SILENCE_RATE", "0.3"))
BASELINE_LATENCY_MS = float(os.environ.get("BRIDGE_BASELINE_LATENCY_MS", "50"))
BASELINE_ECONOMIC_CONVERSION = int(os.environ.get("BRIDGE_BASELINE_ECONOMIC_CONVERSION", "10"))
DRIFT_DEVIATION_THRESHOLD = float(os.environ.get("BRIDGE_DRIFT_DEVIATION_THRESHOLD", "0.5"))


def get_baseline_drift() -> dict:
    """Compute deviation from baseline. If deviation > threshold, emit system_drift event."""
    dl = list(telemetry.decision_latency_ms)
    p50 = sorted(dl)[len(dl) // 2] if dl else 0
    silence_dev = abs(telemetry.silence_rate - BASELINE_SILENCE_RATE)
    latency_dev = abs(p50 - BASELINE_LATENCY_MS) / max(BASELINE_LATENCY_MS, 1)
    econ_dev = abs(telemetry.economic_conversion_count - BASELINE_ECONOMIC_CONVERSION) / max(BASELINE_ECONOMIC_CONVERSION, 1)
    combined = (silence_dev + min(1, latency_dev) + min(1, econ_dev)) / 3
    if combined > DRIFT_DEVIATION_THRESHOLD:
        emit("system_drift", {"deviation": combined, "silence_dev": silence_dev, "latency_dev": latency_dev})

    # Push to Prometheus telemetry
    try:
        from app.services.telemetry import get_telemetry
        _telem = get_telemetry()
        _telem.record_drift("system", combined)
        _telem.update_entropy(telemetry.system_entropy_score)
        if dl:
            _telem.update_swarm_latency(p50, dl[int(len(dl) * 0.99)] if len(dl) > 1 else p50)
    except Exception:
        pass  # Telemetry is optional

    return {
        "silence_deviation": round(silence_dev, 4),
        "latency_deviation": round(latency_dev, 4),
        "economic_deviation": round(econ_dev, 4),
        "combined_deviation": round(combined, 4),
        "threshold": DRIFT_DEVIATION_THRESHOLD,
        "system_drift_emitted": combined > DRIFT_DEVIATION_THRESHOLD,
    }


# =============================================================================
# 5. Economic Risk Governor — Max exposure, cooldown, escalation
# =============================================================================

MAX_EXPOSURE_PER_TWIN = float(os.environ.get("BRIDGE_MAX_EXPOSURE", "1000"))
MAX_EXPOSURE_PER_CYCLE = float(os.environ.get("BRIDGE_MAX_EXPOSURE_PER_CYCLE", "500"))
GLOBAL_EXPOSURE_CEILING = float(os.environ.get("BRIDGE_GLOBAL_EXPOSURE", "10000"))
ECONOMIC_COOLDOWN_SEC = float(os.environ.get("BRIDGE_ECONOMIC_COOLDOWN", "60"))
COOLDOWN_PER_WALLET = ECONOMIC_COOLDOWN_SEC  # alias
_twin_exposure: dict[str, float] = {}
_global_exposure_bucket: float = 0.0
_twin_last_trade: dict[str, float] = {}
_cycle_start = time.time()
_cycle_trade_count = 0
CYCLE_SEC = 3600  # 1 hour


def _reset_cycle_if_needed() -> None:
    global _cycle_start, _cycle_trade_count, _global_exposure_bucket
    if time.time() - _cycle_start > CYCLE_SEC:
        _twin_exposure.clear()
        _global_exposure_bucket = 0.0
        _cycle_start = time.time()
        _cycle_trade_count = 0


def economic_entropy_score() -> float:
    """Financial volatility indicator. High = instability. Autonomy without friction equals instability."""
    total = sum(_twin_exposure.values())
    count = len(_twin_exposure)
    if count == 0:
        return 0.0
    return min(1.0, total / (MAX_EXPOSURE_PER_TWIN * 10) + count * 0.01)


def check_economic_risk(twin_id: str, amount: float) -> tuple[bool, str]:
    """Returns (allowed, reason). Circuit breaker, global ceiling, max_exposure_per_cycle, cooldown enforced."""
    if economic_circuit_breaker_tripped():
        return False, "economic_circuit_breaker_tripped"
    global _global_exposure_bucket
    if _global_exposure_bucket + amount > GLOBAL_EXPOSURE_CEILING:
        return False, "global_exposure_ceiling_exceeded"
    _reset_cycle_if_needed()
    now = time.time()
    exposure = _twin_exposure.get(twin_id, 0) + amount
    last = _twin_last_trade.get(twin_id, 0)
    if exposure > MAX_EXPOSURE_PER_TWIN:
        return False, "max_exposure_exceeded"
    if exposure > MAX_EXPOSURE_PER_CYCLE:
        return False, "max_exposure_per_cycle_exceeded"
    if now - last < COOLDOWN_PER_WALLET:
        return False, "cooldown_active"
    return True, "ok"


def record_economic_action(twin_id: str, amount: float) -> None:
    global _cycle_trade_count, _global_exposure_bucket
    _twin_exposure[twin_id] = _twin_exposure.get(twin_id, 0) + amount
    _global_exposure_bucket += amount
    _twin_last_trade[twin_id] = time.time()
    _cycle_trade_count += 1
    _maybe_trip_circuit_breaker()


# =============================================================================
# 5b. Economic Circuit Breaker — Markets punish naive autonomy
# =============================================================================

CIRCUIT_BREAKER_TRADE_FREQ = int(os.environ.get("BRIDGE_CB_TRADE_FREQ", "50"))  # trades per cycle
CIRCUIT_BREAKER_ENTROPY = float(os.environ.get("BRIDGE_CB_ENTROPY", "0.8"))
_economic_circuit_breaker_tripped = False


def _maybe_trip_circuit_breaker() -> None:
    """Triggers when: trade frequency exceeds threshold, entropy spikes."""
    global _economic_circuit_breaker_tripped
    if _economic_circuit_breaker_tripped:
        return
    if _cycle_trade_count >= CIRCUIT_BREAKER_TRADE_FREQ:
        _economic_circuit_breaker_tripped = True
        return
    if economic_entropy_score() >= CIRCUIT_BREAKER_ENTROPY:
        _economic_circuit_breaker_tripped = True


def economic_circuit_breaker_tripped() -> bool:
    """When True: disable trade capability automatically."""
    return _economic_circuit_breaker_tripped


def reset_economic_circuit_breaker() -> None:
    """Orchestrator can reset after cooldown."""
    global _economic_circuit_breaker_tripped
    _economic_circuit_breaker_tripped = False


# =============================================================================
# 6. Twin Identity Immutability — Stable core. Adaptive edge.
# =============================================================================

IMMUTABLE_IDENTITY_KEYS = frozenset({"core_values", "mission_alignment", "authority_class"})
MUTABLE_LAYER_KEYS = frozenset({"skill_stack", "state", "emotion", "memory"})


def is_identity_key(key: str) -> bool:
    return key in IMMUTABLE_IDENTITY_KEYS


def validate_identity_immutability(update: dict) -> tuple[bool, str]:
    """Reject mutations to immutable identity. Returns (valid, reason)."""
    for k in update:
        if k in IMMUTABLE_IDENTITY_KEYS:
            return False, f"immutable:{k}"
    return True, "ok"


def identity_seal(core_values: str = "", mission_alignment: str = "", authority_class: str = "") -> str:
    """Cryptographic seal. If identity changes without explicit version bump → reject."""
    canonical = json.dumps({
        "core_values": str(core_values),
        "mission_alignment": str(mission_alignment),
        "authority_class": str(authority_class),
    }, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()[:32]


# =============================================================================
# 7. Ethical Conflict Detection — Return silence if conflict > threshold
# =============================================================================

ETHICAL_CONFLICT_THRESHOLD = float(os.environ.get("BRIDGE_ETHICAL_THRESHOLD", "0.7"))


def ethical_conflict_score(action: dict, context: dict) -> float:
    """0 = aligned, 1 = max conflict. Self-contradiction, authority violation, value misalignment."""
    score = 0.0
    if action.get("override_authority"):
        score += 0.5
    if context.get("value_misalignment"):
        score += 0.3
    return min(1.0, score)


def ethical_reason_category(action: dict, context: dict) -> str:
    """Explainable reason category. Ethics must be inspectable."""
    if action.get("override_authority"):
        return "authority_override"
    if context.get("value_misalignment"):
        return "value_misalignment"
    if ethical_conflict_score(action, context) > ETHICAL_CONFLICT_THRESHOLD:
        return "conflict_above_threshold"
    return "aligned"


def should_silence_for_ethics(action: dict, context: dict) -> bool:
    return ethical_conflict_score(action, context) > ETHICAL_CONFLICT_THRESHOLD


# =============================================================================
# 8. Twin Degradation Logic — Stress, cognitive load, performance decay
# =============================================================================

RECOVERY_RATE = float(os.environ.get("BRIDGE_RECOVERY_RATE", "0.1"))  # stress decay per tick


@dataclass
class DegradationState:
    stress: float = 0.0  # 0–1
    cognitive_load: float = 0.0  # 0–1
    performance_factor: float = 1.0  # 1 = full, 0 = degraded
    _last_recovery_tick: float = field(default=0.0, repr=False)

    def accumulate_stress(self, delta: float) -> None:
        self.stress = min(1.0, self.stress + delta)

    def set_cognitive_load(self, load: float) -> None:
        self.cognitive_load = min(1.0, load)

    def decay_under_pressure(self, pressure: float) -> None:
        self.performance_factor = max(0.1, 1.0 - (self.stress + pressure) * 0.5)

    def recovery_tick(self) -> None:
        """Biology heals. Stress decays over time. Performance restores gradually."""
        now = time.time()
        if now - self._last_recovery_tick < 1.0:
            return
        self._last_recovery_tick = now
        self.stress = max(0.0, self.stress - RECOVERY_RATE)
        self.cognitive_load = max(0.0, self.cognitive_load - RECOVERY_RATE * 0.5)
        self.performance_factor = min(1.0, self.performance_factor + RECOVERY_RATE * 0.2)


_degradation: dict[str, DegradationState] = {}


def get_degradation(twin_id: str = "default") -> DegradationState:
    if twin_id not in _degradation:
        _degradation[twin_id] = DegradationState()
    d = _degradation[twin_id]
    d.recovery_tick()
    return d


# =============================================================================
# 9. Simulation Isolation — Simulation state ≠ live canonical state
# =============================================================================

SIMULATION_NAMESPACE = "simulation:"
CANONICAL_NAMESPACE = "canonical:"


def is_simulation_key(key: str) -> bool:
    return key.startswith(SIMULATION_NAMESPACE)


def simulation_key(name: str) -> str:
    return f"{SIMULATION_NAMESPACE}{name}"


def require_commit_for_canonical(simulation_result: dict) -> bool:
    """Simulation does not mutate live state unless explicitly committed."""
    return simulation_result.get("committed", False) is True


def simulation_commit_allowed(
    simulation_result: dict,
    auth: str,
    explicit_commit_flag: bool,
    affects_immutable: bool,
) -> tuple[bool, str]:
    """
    Commit requires: orchestrator authority, explicit commit flag.
    If affecting immutable structures: governance vote required.
    Simulation must not become stealth mutation path.
    """
    if not explicit_commit_flag:
        return False, "explicit_commit_required"
    if auth not in ("orchestrator", "internal"):
        return False, "orchestrator_authority_required"
    if affects_immutable:
        if simulation_result.get("governance_vote") is not True:
            return False, "governance_vote_required_for_immutable"
    return True, "ok"


# =============================================================================
# 10. Upgrade Governance — Proposal → Validation → Sandbox → Commit
# =============================================================================

UPGRADE_STAGES = ("proposal", "validation", "sandbox", "commit")


@dataclass
class UpgradeProposal:
    id: str
    stage: str = "proposal"
    payload: dict = field(default_factory=dict)
    validation_passed: bool = False
    sandbox_tested: bool = False
    rollback_snapshot: dict | None = None


_upgrade_proposals: dict[str, UpgradeProposal] = {}


def propose_upgrade(proposal_id: str, payload: dict) -> UpgradeProposal:
    p = UpgradeProposal(id=proposal_id, payload=payload)
    _upgrade_proposals[proposal_id] = p
    return p


def validate_upgrade(proposal_id: str) -> bool:
    p = _upgrade_proposals.get(proposal_id)
    if not p:
        return False
    # Placeholder: run validation
    p.validation_passed = True
    p.stage = "validation"
    return True


def commit_upgrade(proposal_id: str, snapshot_before_commit: dict | None = None) -> bool:
    """Rollback snapshot before commit. Evolution without rollback is extinction risk."""
    p = _upgrade_proposals.get(proposal_id)
    if not p or not p.validation_passed:
        return False
    p.rollback_snapshot = snapshot_before_commit or {}
    p.stage = "commit"
    return True


def rollback_upgrade(proposal_id: str) -> dict | None:
    """If post-commit telemetry degrades: auto rollback. Returns snapshot to restore."""
    p = _upgrade_proposals.get(proposal_id)
    if not p or not p.rollback_snapshot:
        return None
    return p.rollback_snapshot


# =============================================================================
# 11. Evolution Energy Budget — Real organisms need energy to evolve
# =============================================================================

EVOLUTION_BUDGET_INITIAL = float(os.environ.get("BRIDGE_EVOLUTION_BUDGET", "100"))
EVOLUTION_COST_PER_EVOLVE = 1.0
_evolution_budget = EVOLUTION_BUDGET_INITIAL


def evolution_budget_remaining() -> float:
    return _evolution_budget


def consume_evolution_budget(amount: float = EVOLUTION_COST_PER_EVOLVE) -> bool:
    """Each evolve consumes budget. Returns True if consumed, False if insufficient."""
    global _evolution_budget
    if _evolution_budget < amount:
        return False
    _evolution_budget -= amount
    return True


def replenish_evolution_budget(amount: float, source: str = "unknown") -> None:
    """Budget replenished via: training completion, economic surplus, governance approval."""
    global _evolution_budget
    _evolution_budget = min(EVOLUTION_BUDGET_INITIAL * 2, _evolution_budget + amount)


# =============================================================================
# 12. Drift Detection — Immune system logic
# =============================================================================

DRIFT_THRESHOLD = float(os.environ.get("BRIDGE_DRIFT_THRESHOLD", "0.5"))
_baseline_mission_vector = "poverty reduction, value creation, long-term compounding, integrity"


def drift_score(current_state: dict) -> float:
    """
    Compare current state to baseline mission vector.
    0 = aligned, 1 = max drift.
    Uses: mission_board (backlog, in_progress, review, done), skill count, state_version.
    """
    if not current_state:
        return 0.0
    board = current_state.get("mission_board") or {}
    backlog = board.get("backlog", 0) or 0
    in_progress = board.get("in_progress", 0) or 0
    done = board.get("done", 0) or 0
    total = backlog + in_progress + done
    if total == 0:
        return 0.0
    # High backlog + low done = drift from execution
    stagnation = backlog / total if total > 0 else 0
    completion_ratio = done / total if total > 0 else 0
    return min(1.0, stagnation * 0.6 + (1 - completion_ratio) * 0.4)


def should_trigger_governance(drift: float) -> bool:
    """If drift > threshold: trigger governanceVote or training."""
    return drift > DRIFT_THRESHOLD
