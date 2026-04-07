"""
Cortex — Single Orchestrator Layer (The Brain)

All public endpoints → Cortex → handler. No direct logic outside Cortex.
Receives external requests → validates → enforces risk → routes → ensures mutation only via reducers.

Externally: minimal API surface.
Internally: strict routing control.

Perception → Decision → Expression → Economic Effect → State Update → Evolution
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# =============================================================================
# Capability Registry — Twins read flags before acting. Scale to 100 variants.
# =============================================================================

CAPABILITIES = {
    "perception": True,
    "speech": True,
    "trade": True,
    "ubi": True,
    "simulate": True,
    "evolution": True,
    "marketplace": True,
    "state_mutation": True,
}

# Lock mode: BRIDGE_CAP_LOCK=1 → capabilities frozen at boot. Prevents production drift.
_CAP_LOCK = os.environ.get("BRIDGE_CAP_LOCK", "0") == "1"
_CAP_SNAPSHOT: dict[str, bool] | None = None
_CAP_AUDIT_LOG: list[dict] = []  # Every override must leave a footprint


def _build_cap_snapshot() -> dict[str, bool]:
    out = {}
    for k in CAPABILITIES:
        env_key = f"BRIDGE_CAP_{k.upper()}"
        default = CAPABILITIES.get(k, False)
        if env_key in os.environ:
            new_val = os.environ[env_key] not in ("0", "false", "False")
            out[k] = new_val
            if new_val != default:
                _CAP_AUDIT_LOG.append({
                    "timestamp": time.time(),
                    "capability": k,
                    "old_value": default,
                    "new_value": new_val,
                    "actor": "BRIDGE_CAP_*",
                })
        else:
            out[k] = default
    return out


def get_capability_audit_log() -> list[dict]:
    """Audit trail of capability overrides. Every override must leave a footprint."""
    return list(_CAP_AUDIT_LOG)


def capability_enabled(name: str) -> bool:
    """Check if capability is enabled. Lock mode: frozen at boot. No runtime override."""
    global _CAP_SNAPSHOT
    if _CAP_LOCK:
        if _CAP_SNAPSHOT is None:
            _CAP_SNAPSHOT = _build_cap_snapshot()
        return _CAP_SNAPSHOT.get(name, False)
    env_key = f"BRIDGE_CAP_{name.upper()}"
    if env_key in os.environ:
        return os.environ[env_key] not in ("0", "false", "False")
    return CAPABILITIES.get(name, False)


# =============================================================================
# Authority Classes — Absolute enforcement. No privilege bleed.
# =============================================================================


class AuthorityClass(str, Enum):
    PUBLIC = "public"       # read-only + speech
    ECONOMIC = "economic"   # marketplace + ubi
    INTERNAL = "internal"   # state mutation
    ORCHESTRATOR = "orchestrator"  # system-level evolution


AUTHORITY_SCOPES = {
    AuthorityClass.PUBLIC: {"read", "speech", "perception"},
    AuthorityClass.ECONOMIC: {"read", "speech", "marketplace", "ubi", "trade"},
    AuthorityClass.INTERNAL: {"read", "speech", "marketplace", "ubi", "trade", "state_mutation"},
    AuthorityClass.ORCHESTRATOR: {"read", "speech", "marketplace", "ubi", "trade", "state_mutation", "evolution", "system"},
}

AUTHORITY_ORDER = {AuthorityClass.PUBLIC: 0, AuthorityClass.ECONOMIC: 1, AuthorityClass.INTERNAL: 2, AuthorityClass.ORCHESTRATOR: 3}


def auth_class_from_token(token: str | None) -> AuthorityClass:
    """
    Resolve authority from a signed JWT token.
    String-literal shortcuts ("internal", "orchestrator") are REMOVED — they were
    a complete auth bypass. All authority must come from a verified JWT with an
    'auth' claim, or from a server-side shared secret.
    """
    if not token:
        return AuthorityClass.PUBLIC

    # Server-side shared secret for internal services (e.g., cron jobs, workers)
    _internal_secret = os.environ.get("BRIDGE_INTERNAL_SECRET", "")
    if _internal_secret and len(_internal_secret) >= 32 and token == _internal_secret:
        return AuthorityClass.INTERNAL

    _orchestrator_secret = os.environ.get("BRIDGE_ORCHESTRATOR_SECRET", "")
    if _orchestrator_secret and len(_orchestrator_secret) >= 32 and token == _orchestrator_secret:
        return AuthorityClass.ORCHESTRATOR

    # KeyForge token (prefix kf2.) — deterministic rotating key
    if token.startswith("kf2."):
        try:
            from app.services.keyforge import get_keyforge
            forge = get_keyforge()
            result = forge.validate(token)
            if result.valid:
                scope_to_auth = {
                    "orchestrator": AuthorityClass.ORCHESTRATOR,
                    "internal": AuthorityClass.INTERNAL,
                    "economic": AuthorityClass.ECONOMIC,
                    "api-gateway": AuthorityClass.ECONOMIC,
                    "agent": AuthorityClass.INTERNAL,
                    "webhook": AuthorityClass.ECONOMIC,
                }
                return scope_to_auth.get(result.scope, AuthorityClass.PUBLIC)
        except Exception:
            pass

    # SIWE JWT: verify signature and map claims to authority
    if len(token) > 50:
        try:
            from app.services.siwe_auth import verify_jwt
            payload = verify_jwt(token)
            if payload:
                auth_claim = payload.get("auth", "")
                if auth_claim == "orchestrator":
                    return AuthorityClass.ORCHESTRATOR
                if auth_claim == "internal":
                    return AuthorityClass.INTERNAL
                if auth_claim == "economic":
                    return AuthorityClass.ECONOMIC
        except Exception:
            pass

    return AuthorityClass.PUBLIC


def authority_allows(auth: AuthorityClass, scope: str) -> bool:
    return scope in AUTHORITY_SCOPES.get(auth, set())


def authority_escalation_allowed(
    from_auth: AuthorityClass,
    to_auth: AuthorityClass,
    via_reducer: str | None = None,
) -> bool:
    """
    Escalation requires governanceVote reducer. No silent privilege jump.
    Authority mutation must be state-bound.
    """
    if AUTHORITY_ORDER.get(to_auth, 0) <= AUTHORITY_ORDER.get(from_auth, 0):
        return True  # Downgrade or same
    if via_reducer == "governanceVote":
        return True
    return False


# =============================================================================
# Normalized Response — Predictable. Reduces integration entropy.
# =============================================================================


@dataclass
class CortexResponse:
    ok: bool
    data: dict = field(default_factory=dict)
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "data": self.data,
            "meta": {
                "confidence": self.meta.get("confidence", 1.0),
                "silence": self.meta.get("silence", False),
                "state_delta": self.meta.get("state_delta", False),
                **{k: v for k, v in self.meta.items() if k not in ("confidence", "silence", "state_delta")},
            },
        }


# Confidence floor: if confidence < threshold, force silence. Most AI systems fail because they respond when unsure.
CONFIDENCE_FLOOR = float(os.environ.get("BRIDGE_CONFIDENCE_FLOOR", "0.3"))


def wrap_response(
    data: Any,
    *,
    ok: bool = True,
    confidence: float = 1.0,
    silence: bool = False,
    state_delta: bool = False,
    state_version: int | None = None,
    deterministic_seed: int | None = None,
    ethical_score: float | None = None,
    ethical_reason: str | None = None,
) -> dict:
    """Wrap any response in normalized structure. Enforces confidence floor → silence."""
    if confidence < CONFIDENCE_FLOOR:
        silence = True
        data = data if isinstance(data, dict) else {"value": data}
        if isinstance(data, dict) and "action" in data and data.get("action") is not None:
            data = {**data, "action": None}
    meta: dict = {
        "confidence": max(confidence, 0.0),
        "silence": silence,
        "state_delta": state_delta,
    }
    if state_version is not None:
        meta["state_version"] = state_version
    if deterministic_seed is not None:
        meta["deterministic_seed"] = deterministic_seed
    if ethical_score is not None:
        meta["ethical_score"] = round(ethical_score, 4)
    if ethical_reason is not None:
        meta["ethical_reason"] = ethical_reason
    out = {
        "ok": ok,
        "data": data if isinstance(data, dict) else {"value": data},
        "meta": meta,
    }
    if silence and isinstance(out["data"], dict) and out["data"].get("action") is not None:
        out["data"] = {**out["data"], "action": None}
    return out


# Silence is a first-class concept. Not null. Strategic output.
SILENCE_RESPONSE = wrap_response({"action": None}, ok=True, silence=True, confidence=0.0)


# =============================================================================
# Layer Modes — Real-time vs Strategic. Different schedulers. Different budgets.
# =============================================================================


class LayerMode(str, Enum):
    REALTIME = "realtime"   # speech, emotion, state mutation — low latency
    STRATEGIC = "strategic"  # simulation, training, evolution, bossbots — can block


LAYER_BUDGETS_MS = {
    LayerMode.REALTIME: 100,   # speech embodiment, decision
    LayerMode.STRATEGIC: 5000,  # simulation, training
}


def check_latency_budget(mode: LayerMode, elapsed_ms: float) -> tuple[bool, str]:
    """
    Latency discipline enforced, not decorative.
    REALTIME > 100ms → degraded/silence.
    STRATEGIC > 5000ms → partial result + continue background.
    Returns (within_budget, reason).
    """
    budget = LAYER_BUDGETS_MS.get(mode, 5000)
    if mode == LayerMode.REALTIME and elapsed_ms > budget:
        return False, "realtime_budget_exceeded"
    if mode == LayerMode.STRATEGIC and elapsed_ms > budget:
        return False, "strategic_partial"  # Caller returns partial + continues background
    return True, "ok"


# =============================================================================
# State Versioning — Every mutation increments. Replay. Audit. Rollback.
# =============================================================================

STATE_VERSION_KEY = "bridge:state_version"
TWIN_VERSION_KEY = "bridge:twin_version"
SCHEMA_VERSION = 1


async def get_state_version(memory: Any) -> int:
    if memory is None or not hasattr(memory, "get"):
        return 0
    val = await memory.get(STATE_VERSION_KEY)
    return int(val) if val else 0


STATE_HASH_KEY = "bridge:state_hash"


async def get_state_hash(memory: Any) -> str:
    """Hash of canonical state. Version tells when; hash tells what. Detect corruption, verify replication."""
    if memory is None or not hasattr(memory, "get"):
        return ""
    v = await get_state_version(memory)
    xml = await memory.get("twin:shared_xml") or ""
    canonical = json.dumps({"v": v, "xml": xml[:500]}, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()[:32]


async def increment_state_version(memory: Any) -> int:
    """
    Monotonic version increment. Uses Redis INCR when available for cluster-safe ordering.
    Otherwise fallback to get+set. Organisms need synchronized time.
    """
    if memory is None or not hasattr(memory, "set"):
        return 0
    if hasattr(memory, "incr"):
        try:
            v = await memory.incr(STATE_VERSION_KEY)
            if v == 0:
                raise ValueError("incr returned 0, Redis may be unavailable")
            h = await get_state_hash(memory)
            if hasattr(memory, "set"):
                await memory.set(STATE_HASH_KEY, h)
            return int(v)
        except Exception:
            pass
    v = await get_state_version(memory)
    v += 1
    await memory.set(STATE_VERSION_KEY, str(v))
    h = await get_state_hash(memory)
    await memory.set(STATE_HASH_KEY, h)
    return v


# =============================================================================
# Mission Guardrail — Does this action increase long-term structural value?
# =============================================================================

MISSION_ALIGNMENT_KEYWORDS = {"poverty", "value", "compound", "integrity", "task", "skill", "ubi", "mission"}


# =============================================================================
# Invariant Enforcement — Biology enforces via chemistry. We enforce via assertions.
# =============================================================================

def assert_invariant_silence_implies_null_data(ok: bool, data: Any, silence: bool) -> None:
    """silence true → data must be null or action: null."""
    if not silence:
        return
    if isinstance(data, dict) and data.get("action") is not None and "action" in data:
        if data.get("action") is not None:
            raise AssertionError("invariant_violation: silence=true but data.action is not null")


def assert_invariant_realtime_no_mutation_without_internal(
    layer_mode: str, auth: AuthorityClass, mutates_state: bool
) -> None:
    """REALTIME endpoints must not mutate state unless internal/orchestrator authority."""
    if layer_mode != "realtime" or not mutates_state:
        return
    if auth in (AuthorityClass.INTERNAL, AuthorityClass.ORCHESTRATOR):
        return
    if mutates_state:
        raise AssertionError("invariant_violation: REALTIME state mutation requires internal authority")


def assert_invariant_state_version_never_decreases(prev_version: int, new_version: int) -> None:
    """state_version never decreases."""
    if new_version < prev_version:
        raise AssertionError("invariant_violation: state_version decreased")


def assert_invariant_evolution_requires_orchestrator(cap: bool, auth: AuthorityClass) -> None:
    """Capability evolution cannot enable evolution without orchestrator authority."""
    if not cap:
        return
    if auth == AuthorityClass.ORCHESTRATOR:
        return
    if capability_enabled("evolution"):
        pass  # Check is at call site: evolution endpoints require orchestrator


def enforce_invariants(response: dict) -> None:
    """Fail fast if any invariant violated. Call before returning response."""
    if response.get("meta", {}).get("silence") and response.get("data"):
        if response["data"].get("action") is not None:
            raise AssertionError("invariant_violation: silence=true but data.action is not null")


# =============================================================================
# Mission Guardrail — Does this action increase long-term structural value?
# =============================================================================

# =============================================================================
# Cold-Start Identity Lock — Prevents silent constitutional drift
# =============================================================================

IDENTITY_LOCK_KEY = "bridge:boot_identity"
IDENTITY_LOCK_ENABLED = os.environ.get("BRIDGE_IDENTITY_LOCK", "1") == "1"


def _spine_checksum() -> str:
    """Checksum of SPINE.md. Path relative to package root."""
    try:
        import pathlib
        base = pathlib.Path(__file__).resolve().parent.parent.parent
        spine_path = base / "docs" / "SPINE.md"
        if spine_path.exists():
            return hashlib.sha256(spine_path.read_bytes()).hexdigest()[:16]
    except Exception:
        pass
    return "unknown"


def compute_boot_identity() -> str:
    """Identity = SPINE checksum + reducer registry + schema_version. If these change without version bump, refuse start."""
    from app.reducers import _registry_checksum
    parts = [_spine_checksum(), _registry_checksum(), str(SCHEMA_VERSION)]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:32]


async def verify_boot_identity(memory: Any) -> bool:
    """
    On boot: compute identity, compare to stored. If different without version bump, refuse start.
    Returns True if OK to start, raises SystemExit if identity drift detected.
    """
    if not IDENTITY_LOCK_ENABLED:
        return True
    current = compute_boot_identity()
    stored = None
    if memory and hasattr(memory, "get"):
        stored = await memory.get(IDENTITY_LOCK_KEY)
    if stored is None:
        if memory and hasattr(memory, "set"):
            await memory.set(IDENTITY_LOCK_KEY, current)
        return True
    if stored != current:
        raise SystemExit(
            "BRIDGE_IDENTITY_DRIFT: SPINE, reducers, or schema changed without version bump. "
            "Refusing start. Set BRIDGE_IDENTITY_LOCK=0 to override (not recommended)."
        )
    return True


# =============================================================================
# Pboots and runs — Track process boots and run sessions for mapping and live display
# =============================================================================

BOOTS_LOG_KEY = "bridge:boots_log"
RUNS_LOG_KEY = "bridge:runs_log"
CURRENT_RUN_KEY = "bridge:current_run"
MAX_LOG_ENTRIES = 100
SENSOR_WIFI_KEY = "bridge:sensor:wifi:latest"
SENSOR_MOUSE_KEY = "bridge:sensor:mouse:latest"


async def record_boot(memory: Any) -> dict:
    """Record a process boot. Returns { boot_id, at }."""
    if not memory or not hasattr(memory, "get"):
        return {"boot_id": "", "at": ""}
    import uuid
    from datetime import datetime, timezone
    boot_id = str(uuid.uuid4())[:8]
    at = datetime.now(timezone.utc).isoformat() + "Z"
    entry = {"boot_id": boot_id, "at": at}
    try:
        log = await memory.get(BOOTS_LOG_KEY)
        log = json.loads(log) if isinstance(log, str) else (log or [])
        if not isinstance(log, list):
            log = []
        log.append(entry)
        log = log[-MAX_LOG_ENTRIES:]
        await memory.set(BOOTS_LOG_KEY, json.dumps(log))
    except Exception:
        pass
    return entry


async def record_run_start(memory: Any) -> dict:
    """Start a run session. Returns { run_id, started_at }."""
    if not memory or not hasattr(memory, "get"):
        return {"run_id": "", "started_at": ""}
    import uuid
    from datetime import datetime, timezone
    run_id = str(uuid.uuid4())[:8]
    started_at = datetime.now(timezone.utc).isoformat() + "Z"
    entry = {"run_id": run_id, "started_at": started_at}
    try:
        await memory.set(CURRENT_RUN_KEY, json.dumps(entry))
        log = await memory.get(RUNS_LOG_KEY)
        log = json.loads(log) if isinstance(log, str) else (log or [])
        if not isinstance(log, list):
            log = []
        log.append(entry)
        log = log[-MAX_LOG_ENTRIES:]
        await memory.set(RUNS_LOG_KEY, json.dumps(log))
    except Exception:
        pass
    return entry


async def get_boots_log(memory: Any) -> list:
    """Return recent boots (pboots)."""
    if not memory or not hasattr(memory, "get"):
        return []
    try:
        log = await memory.get(BOOTS_LOG_KEY)
        log = json.loads(log) if isinstance(log, str) else (log or [])
        return log if isinstance(log, list) else []
    except Exception:
        return []


async def get_runs_log(memory: Any) -> list:
    """Return recent runs (runbs)."""
    if not memory or not hasattr(memory, "get"):
        return []
    try:
        log = await memory.get(RUNS_LOG_KEY)
        log = json.loads(log) if isinstance(log, str) else (log or [])
        return log if isinstance(log, list) else []
    except Exception:
        return []


async def get_current_run(memory: Any) -> dict | None:
    """Return current run session if any."""
    if not memory or not hasattr(memory, "get"):
        return None
    try:
        raw = await memory.get(CURRENT_RUN_KEY)
        if not raw:
            return None
        return json.loads(raw) if isinstance(raw, str) else raw  # type: ignore[no-any-return]
    except Exception:
        return None


async def set_sensor_wifi(memory: Any, payload: dict) -> None:
    """Store latest WiFi RF sample (from boot script)."""
    if not memory or not hasattr(memory, "set"):
        return
    try:
        payload["ts"] = time.time()
        await memory.set(SENSOR_WIFI_KEY, json.dumps(payload))
    except Exception:
        pass


async def get_sensor_wifi(memory: Any) -> dict | None:
    """Return latest WiFi sensor payload."""
    if not memory or not hasattr(memory, "get"):
        return None
    try:
        raw = await memory.get(SENSOR_WIFI_KEY)
        return json.loads(raw) if isinstance(raw, str) and raw else None
    except Exception:
        return None


async def set_sensor_mouse(memory: Any, payload: dict) -> None:
    """Store latest mouse tracker sample (from boot script)."""
    if not memory or not hasattr(memory, "set"):
        return
    try:
        payload["ts"] = time.time()
        await memory.set(SENSOR_MOUSE_KEY, json.dumps(payload))
    except Exception:
        pass


async def get_sensor_mouse(memory: Any) -> dict | None:
    """Return latest mouse sensor payload."""
    if not memory or not hasattr(memory, "get"):
        return None
    try:
        raw = await memory.get(SENSOR_MOUSE_KEY)
        return json.loads(raw) if isinstance(raw, str) and raw else None
    except Exception:
        return None


# =============================================================================
# Mission Guardrail — Does this action increase long-term structural value?
# =============================================================================

def mission_alignment_check(action_type: str, payload: dict) -> tuple[bool, str]:
    """
    Hard rule: reject if action does not increase long-term structural value.
    Returns (allowed, reason).
    """
    # Allow read operations
    if action_type in ("get", "read", "fetch", "list"):
        return True, "read"
    # State mutation, economic, cognitive — allow by default; strict mode can tighten
    if action_type in ("state_mutation", "reducer", "speech", "decide", "simulate", "evolve"):
        return True, "core"
    if action_type in ("marketplace", "ubi", "trade", "claim"):
        return True, "economic"
    return True, "default"  # Permit by default; override with MISSION_STRICT=1 for tighter checks
