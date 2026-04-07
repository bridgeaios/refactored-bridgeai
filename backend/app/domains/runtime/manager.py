"""
AOE-RUNTIME Process Manager v2
Hardened single-node orchestrator -- no Docker required.

Ported from BRIDGE_AI_OS/core/app/runtime/manager.py into the unified backend.

Implements:
  - State machine:      STOPPED -> STARTING -> RUNNING -> UNHEALTHY -> FAILED -> FAILED_LOCKED
  - Process identity:   PID + cmd + psutil.create_time()  (prevents PID reuse errors)
  - Restart limits:     MAX_RESTARTS / WINDOW -> FAILED_LOCKED on storm
  - Dependency ordering depends_on resolved before start
  - 3-level health:     process alive  +  port open  +  HTTP endpoint 200
  - Boot reconciliation read registry.json, evict dead PIDs, re-apply restart policies
  - Disk logging:       logs/{service}.log  (append)
  - Port conflict block refuse start if port already bound
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import signal
import socket
import sys
import tempfile
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil
import requests as _requests

# ── Constants ──────────────────────────────────────────────────────────────────

MAX_RESTARTS        = 5
RESTART_WINDOW      = 60    # seconds
SUPERVISOR_TICK     = 5     # seconds between supervisor sweeps
HEALTH_HTTP_TIMEOUT = 2     # seconds for HTTP health ping
HEALTH_WAIT_SECS    = 5     # seconds to wait for a service to become healthy
INTEGRITY_INTERVAL  = 30    # seconds between integrity check sweeps
LOG_LINES_BUFFER    = 500   # in-memory ring per service

SINGLETON_SERVICES = ["backend", "redis", "gateway"]

SYSTEM_MODE = os.getenv("AOE_MODE", "CONSOLIDATED")

_registry_checksum: Optional[str] = None

# ── Atomic registry write ───────────────────────────────────────────────────────

def write_registry_atomic(data: dict, path: Path) -> None:
    temp_fd, temp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(temp_path, path)
    except Exception:
        try:
            os.unlink(temp_path)
        except Exception:
            pass


def registry_hash(data: dict) -> str:
    serializable = {}
    for name, st in data.items():
        serializable[name] = {
            "status": st.status,
            "pid": st.identity.pid if st.identity else None,
            "cmd": st.identity.cmd if st.identity else None,
            "start_time": st.identity.start_time if st.identity else None,
        }
    return hashlib.sha256(json.dumps(serializable, sort_keys=True).encode()).hexdigest()


def enforce_singleton(name: str, registry: dict) -> None:
    if name not in SINGLETON_SERVICES:
        return
    for svc, sig in registry.items():
        if svc != name and svc.startswith(name) and sig.get("status") == State.RUNNING:
            if validate_signature(sig):
                raise Exception(f"{name} already running as {svc}")


# ── Paths ──────────────────────────────────────────────────────────────────────

_HERE         = Path(__file__).parent
SERVICES_PATH = _HERE / "services.json"
REGISTRY_PATH = _HERE / "registry.json"
LOGS_DIR      = _HERE / "logs"
LOGS_DIR.mkdir(exist_ok=True)

logger = logging.getLogger("aoe.runtime")


# ── State machine ─────────────────────────────────────────────────────────────

class State:
    STOPPED       = "stopped"
    STARTING      = "starting"
    RUNNING       = "running"
    UNHEALTHY     = "unhealthy"
    FAILED        = "failed"
    FAILED_LOCKED = "failed_locked"


# ── Data models ────────────────────────────────────────────────────────────────

@dataclass
class ServiceDef:
    name:           str
    description:    str
    command:        str
    cwd:            str
    env:            Dict[str, str]
    ports:          List[int]
    depends_on:     List[str]
    restart_policy: str
    health:         Optional[str]
    tier:           int
    drive:          str


@dataclass
class ProcessIdentity:
    pid:        int
    cmd:        str
    start_time: float


@dataclass
class RestartRecord:
    timestamps: deque = field(default_factory=lambda: deque(maxlen=MAX_RESTARTS + 1))

    def record(self) -> None:
        self.timestamps.append(time.time())

    def count_in_window(self) -> int:
        cutoff = time.time() - RESTART_WINDOW
        return sum(1 for t in self.timestamps if t > cutoff)


@dataclass
class ServiceState:
    name:           str
    status:         str           = State.STOPPED
    identity:       Optional[ProcessIdentity] = None
    restarts:       int           = 0
    restart_record: RestartRecord = field(default_factory=RestartRecord)
    started_at:     Optional[float] = None
    last_exit_code: Optional[int]   = None
    logs:           deque         = field(default_factory=lambda: deque(maxlen=LOG_LINES_BUFFER))


# ── Process identity ──────────────────────────────────────────────────────────

def build_signature(proc_pid: int, cmd: str) -> dict:
    create_time = time.time()
    try:
        create_time = psutil.Process(proc_pid).create_time()
    except Exception:
        pass
    return {"pid": proc_pid, "cmd": cmd, "start_time": create_time}


def validate_signature(sig: dict) -> bool:
    if not sig:
        return False
    try:
        p = psutil.Process(sig["pid"])
        cmdline_match = " ".join(p.cmdline()) == sig.get("cmd", "")
        time_match    = abs(p.create_time() - sig["start_time"]) < 1.0
        return p.is_running() and p.status() != psutil.STATUS_ZOMBIE and time_match and cmdline_match
    except Exception:
        return False


# ── Port utilities ─────────────────────────────────────────────────────────────

def _port_bound(port: int) -> bool:
    try:
        for c in psutil.net_connections(kind="inet"):
            if c.laddr and c.laddr.port == port:
                return True
    except Exception:
        pass
    s = socket.socket()
    try:
        s.connect(("127.0.0.1", port))
        return True
    except Exception:
        return False
    finally:
        s.close()


def port_in_use(port: int) -> bool:
    return _port_bound(port)


# ── Health check (3-level) ────────────────────────────────────────────────────

def _check_health(defn: ServiceDef, identity: Optional[ProcessIdentity]) -> dict:
    process_ok = False
    if identity:
        sig = {"pid": identity.pid, "cmd": identity.cmd, "start_time": identity.start_time}
        process_ok = validate_signature(sig)

    ports_ok = True
    if defn.ports:
        ports_ok = all(_port_bound(p) for p in defn.ports)

    endpoint_ok = True
    if defn.health:
        try:
            r = _requests.get(defn.health, timeout=HEALTH_HTTP_TIMEOUT)
            endpoint_ok = r.status_code == 200
        except Exception:
            endpoint_ok = False

    return {
        "process":  process_ok,
        "port":     ports_ok,
        "endpoint": endpoint_ok,
        "healthy":  process_ok and ports_ok and endpoint_ok,
    }


# ── Restart limiter ──────────────────────────────────────────────────────────

RESTART_LIMIT  = MAX_RESTARTS
_restart_history: Dict[str, deque] = {}


def can_restart(name: str) -> bool:
    now = time.time()
    q   = _restart_history.setdefault(name, deque())
    while q and now - q[0] > RESTART_WINDOW:
        q.popleft()
    if len(q) >= RESTART_LIMIT:
        return False
    q.append(now)
    return True


def restart_count_in_window(name: str) -> int:
    now = time.time()
    q   = _restart_history.get(name, deque())
    return sum(1 for t in q if now - t <= RESTART_WINDOW)


# ── Manager ───────────────────────────────────────────────────────────────────

class AOEProcessManager:
    """Lightweight, Docker-free process orchestrator."""

    def __init__(self) -> None:
        self._defs:   Dict[str, ServiceDef]   = {}
        self._states: Dict[str, ServiceState] = {}
        self._procs:  Dict[str, asyncio.subprocess.Process] = {}
        self._lock    = asyncio.Lock()
        self._start_locks: Dict[str, bool] = {}
        self._supervisor_task: Optional[asyncio.Task] = None
        self._load_definitions()
        self._reconcile_registry()

    # ── Boot ──────────────────────────────────────────────────────────────────

    def _load_definitions(self) -> None:
        if not SERVICES_PATH.exists():
            return
        data = json.loads(SERVICES_PATH.read_text(encoding="utf-8"))
        for name, cfg in data.get("services", {}).items():
            fields = {k: v for k, v in cfg.items() if k in ServiceDef.__dataclass_fields__}
            self._defs[name]   = ServiceDef(**fields)
            self._states[name] = ServiceState(name=name)

    def _reconcile_registry(self) -> None:
        if not REGISTRY_PATH.exists():
            return
        try:
            data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        except Exception:
            return

        for name, info in data.items():
            sig = {
                "pid":        info.get("pid"),
                "cmd":        info.get("cmd", ""),
                "start_time": info.get("start_time", 0.0),
            }
            if name not in self._states:
                self._states[name] = ServiceState(name=name)
            st = self._states[name]

            if validate_signature(sig):
                st.status     = State.RUNNING
                st.identity   = ProcessIdentity(
                    pid=sig["pid"], cmd=sig["cmd"], start_time=sig["start_time"]
                )
                st.started_at = info.get("started_at")
                self._log_disk(name, f"[reconcile] re-attached PID {sig['pid']}")
            else:
                st.status   = State.STOPPED
                st.identity = None
                defn = self._defs.get(name)
                if defn and defn.restart_policy == "always":
                    self._log_disk(name, f"[reconcile] PID {sig.get('pid')} dead, queued for restart")

        self._save_registry()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _save_registry(self) -> None:
        out: Dict[str, Any] = {}
        for name, st in self._states.items():
            defn = self._defs.get(name)
            entry: Dict[str, Any] = {
                "status":     st.status,
                "port":       defn.ports[0] if defn and defn.ports else None,
                "ports":      defn.ports    if defn else [],
                "started_at": st.started_at,
            }
            if st.identity:
                entry.update({
                    "pid":        st.identity.pid,
                    "cmd":        st.identity.cmd,
                    "start_time": st.identity.start_time,
                })
            out[name] = entry
        try:
            write_registry_atomic(out, REGISTRY_PATH)
        except Exception:
            pass

    # ── Disk logging ──────────────────────────────────────────────────────────

    def _log_disk(self, name: str, line: str) -> None:
        st = self._states.get(name)
        if st:
            st.logs.append(line)
        try:
            log_path = LOGS_DIR / f"{name}.log"
            with log_path.open("a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {line}\n")
        except Exception:
            pass

    # ── Dependency resolution ─────────────────────────────────────────────────

    async def _start_deps(self, name: str, visited: Optional[set] = None) -> dict:
        if visited is None:
            visited = set()
        if name in visited:
            return {"ok": True}
        visited.add(name)

        defn = self._defs.get(name)
        if not defn:
            return {"ok": True}

        for dep in defn.depends_on:
            dep_st = self._states.get(dep)
            if dep_st and dep_st.status == State.RUNNING:
                continue
            res = await self._start_deps(dep, visited)
            if not res["ok"]:
                return res
            res = await self._do_start(dep)
            if not res["ok"]:
                return {"ok": False, "error": f"dependency '{dep}' failed to start: {res.get('error')}"}
            await asyncio.sleep(2)
        return {"ok": True}

    # ── Port validation ───────────────────────────────────────────────────────

    def validate_ports(self, name: str) -> Optional[str]:
        defn = self._defs.get(name)
        if not defn:
            return None
        for p in defn.ports:
            for other_name, other_def in self._defs.items():
                if other_name == name:
                    continue
                if p in other_def.ports:
                    other_st = self._states.get(other_name)
                    if other_st and other_st.status == State.RUNNING:
                        return f"port {p} held by running service '{other_name}'"
            if port_in_use(p):
                return f"port {p} already in use"
        return None

    # ── Start / Stop / Restart ────────────────────────────────────────────────

    async def start(self, name: str) -> dict:
        async with self._lock:
            dep_result = await self._start_deps(name)
            if not dep_result["ok"]:
                return dep_result
            return await self._do_start(name)

    async def _do_start(self, name: str) -> dict:
        if name not in self._defs:
            return {"ok": False, "error": f"Unknown service: {name}"}

        defn = self._defs[name]
        st   = self._states[name]

        if SYSTEM_MODE == "CONSOLIDATED":
            registry: Dict[str, Any] = {}
            for n, s in self._states.items():
                if s.identity:
                    registry[n] = {
                        "status": s.status,
                        "pid": s.identity.pid,
                        "cmd": s.identity.cmd,
                        "start_time": s.identity.start_time,
                    }
            try:
                enforce_singleton(name, registry)
            except Exception as e:
                return {"ok": False, "error": str(e)}

        dep_result = await self.ensure_dependencies(name)
        if not dep_result["ok"]:
            self._log_disk(name, f"[start] blocked by dependency: {dep_result['error']}")
            st.status = State.FAILED
            self._save_registry()
            return dep_result

        if st.status == State.RUNNING and st.identity:
            sig = {"pid": st.identity.pid, "cmd": st.identity.cmd, "start_time": st.identity.start_time}
            if validate_signature(sig):
                return {"ok": False, "error": f"{name} already running (PID {st.identity.pid})"}
            st.status   = State.FAILED
            st.identity = None

        if st.status == State.FAILED_LOCKED:
            return {"ok": False, "error": f"{name} is FAILED_LOCKED -- clear with 'aoe unlock {name}'"}

        conflict = self.validate_ports(name)
        if conflict:
            return {"ok": False, "error": conflict}

        cwd = defn.cwd if os.path.isdir(defn.cwd) else os.getcwd()
        env = {**os.environ, **defn.env}

        is_win    = sys.platform.startswith("win")
        shell_cmd = (["powershell", "-NoProfile", "-Command", defn.command]
                     if is_win else ["bash", "-c", defn.command])

        st.status = State.STARTING
        try:
            extra: Dict[str, Any] = {"creationflags": 0x08000000} if is_win else {}
            proc = await asyncio.create_subprocess_exec(
                *shell_cmd,
                cwd=cwd, env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                **extra,
            )
            self._procs[name] = proc

            sig = build_signature(proc.pid, defn.command)
            st.identity = ProcessIdentity(
                pid=sig["pid"], cmd=sig["cmd"], start_time=sig["start_time"]
            )
            st.status     = State.RUNNING
            st.started_at = time.time()
            self._save_registry()
            self._log_disk(name, f"[start] PID {proc.pid}")

            asyncio.create_task(self._capture_logs(name, proc))
            return {"ok": True, "pid": proc.pid, "name": name}

        except Exception as e:
            st.status = State.FAILED
            self._log_disk(name, f"[start error] {e}")
            return {"ok": False, "error": str(e)}

    async def stop(self, name: str) -> dict:
        async with self._lock:
            return await self._do_stop(name)

    async def _do_stop(self, name: str) -> dict:
        st   = self._states.get(name)
        proc = self._procs.get(name)

        if not st or st.status not in (State.RUNNING, State.STARTING, State.UNHEALTHY):
            return {"ok": False, "error": f"{name} is not running (state: {st.status if st else 'unknown'})"}

        if proc:
            try:
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5)
                except asyncio.TimeoutError:
                    proc.kill()
            except Exception:
                pass
            self._procs.pop(name, None)
        elif st.identity:
            try:
                sig = signal.SIGTERM if not sys.platform.startswith("win") else signal.SIGBREAK
                os.kill(st.identity.pid, sig)
            except Exception:
                pass

        st.status   = State.STOPPED
        st.identity = None
        self._save_registry()
        self._log_disk(name, "[stop] requested")
        return {"ok": True, "name": name}

    async def restart(self, name: str) -> dict:
        await self._do_stop(name)
        await asyncio.sleep(0.5)
        return await self._do_start(name)

    def unlock(self, name: str) -> dict:
        st = self._states.get(name)
        if not st:
            return {"ok": False, "error": f"Unknown: {name}"}
        st.status = State.STOPPED
        st.restart_record = RestartRecord()
        self._log_disk(name, "[unlock] manual reset")
        return {"ok": True, "name": name}

    # ── Status / List ─────────────────────────────────────────────────────────

    def status(self, name: str) -> dict:
        if name not in self._defs:
            return {"ok": False, "error": f"Unknown service: {name}"}
        st   = self._states[name]
        defn = self._defs[name]
        if st.identity and st.status == State.RUNNING:
            h = _check_health(defn, st.identity)
            if not h["process"]:
                st.status   = State.FAILED
                st.identity = None
        return {
            "ok":          True,
            "name":        name,
            "status":      st.status,
            "pid":         st.identity.pid if st.identity else None,
            "ports":       defn.ports,
            "tier":        defn.tier,
            "drive":       defn.drive,
            "depends_on":  defn.depends_on,
            "restarts":    st.restarts,
            "started_at":  st.started_at,
            "restart_policy": defn.restart_policy,
            "description": defn.description,
        }

    def list_services(self) -> list:
        return sorted(
            [self.status(n) for n in self._defs],
            key=lambda x: (x.get("tier", 9), x["name"])
        )

    # ── Health ────────────────────────────────────────────────────────────────

    def health_check(self, name: str) -> dict:
        defn = self._defs.get(name)
        st   = self._states.get(name)
        if not defn or not st:
            return {"healthy": False, "error": "unknown service"}
        return _check_health(defn, st.identity if st else None)

    # ── Logs ──────────────────────────────────────────────────────────────────

    def logs(self, name: str, lines: int = 50) -> list:
        log_path = LOGS_DIR / f"{name}.log"
        if log_path.exists():
            try:
                all_lines = log_path.read_text(encoding="utf-8").splitlines()
                return all_lines[-lines:]
            except Exception:
                pass
        st = self._states.get(name)
        return list(st.logs)[-lines:] if st else []

    # ── Port conflict scan ────────────────────────────────────────────────────

    def scan_conflicts(self) -> list:
        seen: Dict[int, str] = {}
        conflicts: list = []
        for name, defn in self._defs.items():
            for port in defn.ports:
                if port in seen:
                    conflicts.append({"port": port, "a": seen[port], "b": name})
                else:
                    seen[port] = name
        return conflicts

    # ── Supervisor ────────────────────────────────────────────────────────────

    async def start_supervisor(self) -> None:
        for name, defn in self._defs.items():
            st = self._states.get(name)
            if st and st.status == State.STOPPED and defn.restart_policy == "always":
                try:
                    await self._do_start(name)
                except Exception:
                    pass

        while True:
            await asyncio.sleep(SUPERVISOR_TICK)

            for name in list(self._defs.keys()):
                defn = self._defs[name]
                st   = self._states.get(name)
                if not st:
                    continue

                state = st.status

                if state in (State.RUNNING, State.UNHEALTHY):
                    healthy = _check_health(defn, st.identity)["healthy"]
                    if healthy:
                        if state != State.RUNNING:
                            self._log_disk(name, "[supervisor] recovered -> RUNNING")
                        st.status = State.RUNNING
                    else:
                        if state == State.RUNNING:
                            self._log_disk(name, "[supervisor] degraded -> UNHEALTHY")
                        st.status = State.UNHEALTHY
                        if getattr(st, "_unhealthy_ticks", 0) >= 1:
                            st.status = State.FAILED
                            st._unhealthy_ticks = 0
                            self._log_disk(name, "[supervisor] UNHEALTHYx2 -> FAILED")
                        else:
                            st._unhealthy_ticks = getattr(st, "_unhealthy_ticks", 0) + 1

                elif state in (State.STOPPED, State.FAILED):
                    if self._start_locks.get(name, False):
                        continue
                    self._start_locks[name] = True
                    try:
                        should = (
                            defn.restart_policy == "always"
                            or (defn.restart_policy == "on-failure"
                                and st.last_exit_code not in (0, None))
                        )
                        if not should:
                            continue

                        if can_restart(name):
                            st.restarts += 1
                            st.status = State.STARTING
                            self._log_disk(name,
                                f"[supervisor] restart #{st.restarts} "
                                f"(window={restart_count_in_window(name)}/{RESTART_LIMIT})")
                            try:
                                await self._do_start(name)
                            except Exception as e:
                                st.status = State.FAILED
                                self._log_disk(name, f"[supervisor] restart error: {e}")
                        else:
                            st.status = State.FAILED_LOCKED
                            self._log_disk(
                                name,
                                f"[supervisor] FAILED_LOCKED -- >={RESTART_LIMIT} restarts "
                                f"in {RESTART_WINDOW}s. Run 'aoe unlock {name}' to reset."
                            )
                    finally:
                        self._start_locks[name] = False

                elif state == State.FAILED_LOCKED:
                    continue

    # ── Log capture ───────────────────────────────────────────────────────────

    async def _capture_logs(self, name: str, proc: asyncio.subprocess.Process) -> None:
        st = self._states.get(name)
        try:
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").rstrip()
                self._log_disk(name, text)
        except Exception:
            pass

        rc = await proc.wait()
        if st:
            st.last_exit_code = rc
            if st.status == State.RUNNING:
                st.status = State.STOPPED if rc == 0 else State.FAILED
        self._procs.pop(name, None)
        self._save_registry()
        self._log_disk(name, f"[exit] code={rc}")

    # ── Consolidation engine ──────────────────────────────────────────────────

    async def run_consolidation(self) -> list:
        PHASES = [
            ["dromedaries-db"],
            ["backend"],
            ["state-loop"],
            ["executor"],
            ["frontend", "ui"],
            ["gateway"],
        ]
        PHASE_LABELS = [
            "Core Data (DB)",
            "Backend",
            "State Loop",
            "Executor Cluster",
            "UI + Frontend",
            "Gateway",
        ]

        try:
            raw = json.loads(SERVICES_PATH.read_text(encoding="utf-8"))
            file_phases = raw.get("consolidation_phases", [])
            if file_phases:
                PHASES = [ph["services"] for ph in file_phases]
                PHASE_LABELS = [ph.get("label", f"Phase {i+1}") for i, ph in enumerate(file_phases)]
        except Exception:
            pass

        results: list = []
        for i, (svcs, label) in enumerate(zip(PHASES, PHASE_LABELS)):
            phase_num   = i + 1
            svc_results: list = []
            phase_ok    = True

            for svc_name in svcs:
                res = await self._do_start(svc_name)
                svc_results.append({"service": svc_name, **res})
                if not res["ok"]:
                    phase_ok = False

            if not phase_ok:
                results.append({
                    "phase": phase_num, "label": label,
                    "ok": False, "services": svc_results,
                })
                results.append({
                    "phase": phase_num + 0.5,
                    "label": "BLOCKED -- phase failed, halting consolidation",
                    "ok": False, "services": [],
                })
                break

            health_results: list = []
            for svc_name in svcs:
                defn = self._defs.get(svc_name)
                st   = self._states.get(svc_name)
                if not defn:
                    continue
                waited = 0
                h: Dict[str, Any] = {"healthy": False}
                while waited < 30:
                    h = _check_health(defn, st.identity if st else None)
                    if h["healthy"]:
                        break
                    await asyncio.sleep(1)
                    waited += 1
                health_results.append({
                    "service": svc_name,
                    "healthy": h["healthy"],
                    "waited_s": waited,
                })
                if not h["healthy"]:
                    phase_ok = False

            results.append({
                "phase":   phase_num,
                "label":   label,
                "ok":      phase_ok,
                "services": svc_results,
                "health":   health_results,
            })

            if not phase_ok:
                results.append({
                    "phase": phase_num + 0.5,
                    "label": "BLOCKED -- services did not become healthy",
                    "ok": False, "services": [],
                })
                break

        return results

    # ── Health wait helper ────────────────────────────────────────────────────

    async def wait_healthy(self, name: str, timeout: int = HEALTH_WAIT_SECS) -> bool:
        defn = self._defs.get(name)
        st = self._states.get(name)
        if not defn:
            return False
        waited = 0
        while waited < timeout:
            h = _check_health(defn, st.identity if st else None)
            if h["healthy"]:
                return True
            await asyncio.sleep(1)
            waited += 1
        return False

    # ── Dependency health validation ──────────────────────────────────────────

    async def ensure_dependencies(self, name: str) -> dict:
        defn = self._defs.get(name)
        if not defn:
            return {"ok": True}
        for dep in defn.depends_on:
            dep_st = self._states.get(dep)
            if not dep_st or dep_st.status != State.RUNNING:
                return {"ok": False, "error": f"dependency '{dep}' not running"}
            if not await self.wait_healthy(dep, timeout=HEALTH_WAIT_SECS):
                return {"ok": False, "error": f"dependency '{dep}' not healthy"}
        return {"ok": True}

    # ── Integrity check loop ──────────────────────────────────────────────────

    async def start_integrity_loop(self) -> None:
        global _registry_checksum

        while True:
            await asyncio.sleep(INTEGRITY_INTERVAL)

            current_hash = registry_hash(self._states)

            if _registry_checksum is not None and current_hash != _registry_checksum:
                logger.warning(
                    "[integrity] registry checksum mismatch: "
                    "%s != %s", current_hash[:16], _registry_checksum[:16]
                )
            _registry_checksum = current_hash

            for name, st in self._states.items():
                if st.status != State.RUNNING or not st.identity:
                    continue
                defn = self._defs.get(name)
                if not defn:
                    continue
                sig = {"pid": st.identity.pid, "cmd": st.identity.cmd, "start_time": st.identity.start_time}
                if not validate_signature(sig):
                    self._log_disk(name, "[integrity] signature invalid -> marking FAILED")
                    st.status = State.FAILED
                    st.identity = None
                    self._save_registry()


# ── Singleton ─────────────────────────────────────────────────────────────────

_manager: Optional[AOEProcessManager] = None


def get_manager() -> AOEProcessManager:
    global _manager
    if _manager is None:
        _manager = AOEProcessManager()
    return _manager
