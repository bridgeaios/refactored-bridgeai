"""
Phase 4 — Control Plane: Global Invariant Enforcement Engine

Runs an async loop every CYCLE_INTERVAL seconds. Each cycle:
  1. Checks all invariants (L1, L2, L9, L10, L27)
  2. Persists violation state to StateEngine
  3. Updates the TreasuryGate (unlocked iff all pass)
  4. Logs structured audit entry per cycle

Fail posture: CLOSED — treasury stays locked until all invariants pass.
             Process stays alive to serve health checks even under violation.
             Only the treasury commit path is blocked, not reads.

TreasuryGate is a module-level singleton used by TreasuryService.collect()
to check unlock status before processing any financial event.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.state_engine import StateEngine
    from app.core.safe_spawn import live_tasks

_log = logging.getLogger("control_plane")

CYCLE_INTERVAL = 5.0  # seconds between enforcement cycles
STATE_KEY = "control:invariants"
VIOLATION_KEY = "control:violations"

# ---------------------------------------------------------------------------
# Treasury Gate — singleton checked by TreasuryService before every commit
# ---------------------------------------------------------------------------

@dataclass
class _TreasuryGate:
    _locked: bool = True
    _reason: str = "Control plane not yet run"
    _last_checked: float = 0.0

    def lock(self, reason: str) -> None:
        if not self._locked:
            _log.warning("[TREASURY GATE] LOCKED — %s", reason)
        self._locked = True
        self._reason = reason
        self._last_checked = time.time()

    def unlock(self) -> None:
        if self._locked:
            _log.info("[TREASURY GATE] UNLOCKED — all invariants satisfied")
        self._locked = False
        self._reason = ""
        self._last_checked = time.time()

    @property
    def is_open(self) -> bool:
        return not self._locked

    def check(self) -> None:
        """Raise RuntimeError if treasury is locked. Call inside TreasuryService.collect()."""
        if self._locked:
            raise RuntimeError(
                f"Treasury gate locked: {self._reason}. "
                "Invariant enforcement must pass before financial operations are permitted."
            )

    def status(self) -> dict:
        return {
            "open": self.is_open,
            "reason": self._reason,
            "last_checked": self._last_checked,
        }


TREASURY_GATE = _TreasuryGate()


# ---------------------------------------------------------------------------
# Invariant check functions
# Each returns (passed: bool, detail: str)
# ---------------------------------------------------------------------------

async def _check_L1_tunnel(engine: "StateEngine") -> tuple[bool, str]:
    """
    L1 TUNNEL — verify the StateEngine pipeline is active and writable.
    Writes a probe key and reads it back to confirm round-trip integrity.
    """
    probe_key = "control:L1_probe"
    probe_val = f"probe_{int(time.time())}"
    try:
        await engine.set(probe_key, probe_val)
        read_back = await engine.get(probe_key)
        if str(read_back) != probe_val:
            return False, f"read-back mismatch: wrote {probe_val!r}, got {read_back!r}"
        return True, "pipeline round-trip OK"
    except Exception as exc:
        return False, f"pipeline error: {exc}"


async def _check_L2_gatekeeper(engine: "StateEngine") -> tuple[bool, str]:
    """
    L2 GATEKEEPER — confirm SQLite is in WAL mode (concurrent-read, single-write).
    """
    try:
        db = engine._require_db()
        async with db.execute("PRAGMA journal_mode") as cur:
            row = await cur.fetchone()
        mode = row[0] if row else ""
        if mode != "wal":
            return False, f"journal_mode={mode!r}, expected 'wal'"
        return True, f"journal_mode=wal"
    except Exception as exc:
        return False, f"gatekeeper check error: {exc}"


def _check_L9_secrets() -> tuple[bool, str]:
    """
    L9 SECRETS — confirm rotation confirmation token is present.
    secrets_guard.enforce() already ran at boot; this is the continuous check
    to ensure the env var hasn't been unset at runtime.
    """
    rotated = os.environ.get("BRIDGE_SECRETS_ROTATED", "").strip()
    env_mode = os.environ.get("BRIDGE_ENV", os.environ.get("ENV", "development")).lower()
    if not rotated and env_mode == "production":
        return False, "BRIDGE_SECRETS_ROTATED not set in production mode"
    return True, "secrets rotation confirmed (or dev mode)"


def _check_L10_doctrine() -> tuple[bool, str]:
    """
    L10 DOCTRINE — verify all known background tasks are registered via safe_spawn.
    Any task that bypassed safe_spawn won't appear in the registry; we detect orphans
    by comparing asyncio's all_tasks() against the registry names.
    """
    try:
        from app.core.safe_spawn import live_tasks as _live_tasks
        registered = set(_live_tasks().keys())
        all_tasks = {t.get_name() for t in asyncio.all_tasks() if not t.done()}
        # Filter out internal asyncio tasks and the control loop itself
        untracked = {
            name for name in all_tasks
            if name not in registered
            and not name.startswith("Task-")        # asyncio auto-named
            and name != "control_plane"             # ourselves
            and not name.startswith("asyncio")
        }
        if untracked:
            return False, f"untracked tasks outside safe_spawn: {sorted(untracked)}"
        return True, f"all {len(registered)} tracked tasks accounted for"
    except Exception as exc:
        return False, f"doctrine check error: {exc}"


async def _check_L27_idempotency(engine: "StateEngine") -> tuple[bool, str]:
    """
    L27 EXTENDED — confirm the idempotency table exists and is writable.
    """
    try:
        db = engine._require_db()
        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='idempotency'"
        ) as cur:
            row = await cur.fetchone()
        if row is None:
            return False, "idempotency table missing"
        # Confirm writable with a test claim (use a fixed sentinel key)
        sentinel = "__L27_health_probe__"
        await engine.claim_idempotency(sentinel, "health")
        return True, "idempotency table present and writable"
    except Exception as exc:
        return False, f"idempotency check error: {exc}"


# ---------------------------------------------------------------------------
# Cycle runner
# ---------------------------------------------------------------------------

@dataclass
class InvariantResult:
    name: str
    passed: bool
    detail: str
    ts: float = field(default_factory=time.time)


async def run_cycle(engine: "StateEngine") -> list[InvariantResult]:
    """
    Execute one enforcement cycle. Returns results for all invariants.
    Updates TREASURY_GATE and persists state.
    """
    checks: list[InvariantResult] = []

    L1_passed, L1_detail = await _check_L1_tunnel(engine)
    checks.append(InvariantResult("L1_TUNNEL", L1_passed, L1_detail))

    L2_passed, L2_detail = await _check_L2_gatekeeper(engine)
    checks.append(InvariantResult("L2_GATEKEEPER", L2_passed, L2_detail))

    L9_passed, L9_detail = _check_L9_secrets()
    checks.append(InvariantResult("L9_SECRETS", L9_passed, L9_detail))

    L10_passed, L10_detail = _check_L10_doctrine()
    checks.append(InvariantResult("L10_DOCTRINE", L10_passed, L10_detail))

    L27_passed, L27_detail = await _check_L27_idempotency(engine)
    checks.append(InvariantResult("L27_IDEMPOTENCY", L27_passed, L27_detail))

    violations = [r for r in checks if not r.passed]
    all_passed = len(violations) == 0

    # Update treasury gate
    if all_passed:
        TREASURY_GATE.unlock()
    else:
        reason = "; ".join(f"{r.name}: {r.detail}" for r in violations)
        TREASURY_GATE.lock(reason)

    # Persist state snapshot to SQLite
    snapshot = {
        "ts": time.time(),
        "all_passed": all_passed,
        "results": [
            {"name": r.name, "passed": r.passed, "detail": r.detail, "ts": r.ts}
            for r in checks
        ],
        "treasury_gate": TREASURY_GATE.status(),
    }
    try:
        await engine.set(STATE_KEY, snapshot)
        if violations:
            await engine.append(VIOLATION_KEY, {
                "ts": time.time(),
                "violations": [r.name for r in violations],
                "details": {r.name: r.detail for r in violations},
            }, max_len=200)
    except Exception:
        _log.exception("Failed to persist control plane state")

    # Structured log
    if violations:
        _log.error(
            "[CONTROL PLANE] cycle FAIL — violations: %s",
            {r.name: r.detail for r in violations},
        )
    else:
        _log.debug("[CONTROL PLANE] cycle OK — treasury gate open")

    return checks


# ---------------------------------------------------------------------------
# Continuous enforcement loop
# ---------------------------------------------------------------------------

async def control_loop(engine: "StateEngine") -> None:
    """
    Continuous async enforcement loop. Spawned via safe_spawn as 'control_plane'.
    Runs every CYCLE_INTERVAL seconds indefinitely.
    """
    _log.info("[CONTROL PLANE] starting enforcement loop (interval=%.1fs)", CYCLE_INTERVAL)
    cycle = 0
    while True:
        cycle += 1
        try:
            results = await run_cycle(engine)
            if cycle % 60 == 0:  # log summary every 5 minutes
                passed = sum(1 for r in results if r.passed)
                _log.info("[CONTROL PLANE] cycle %d — %d/%d invariants OK", cycle, passed, len(results))
        except asyncio.CancelledError:
            _log.info("[CONTROL PLANE] loop cancelled — shutting down cleanly")
            raise
        except Exception:
            _log.exception("[CONTROL PLANE] unexpected error in enforcement cycle %d", cycle)
        await asyncio.sleep(CYCLE_INTERVAL)
