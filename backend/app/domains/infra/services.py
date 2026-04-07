"""
Infra domain service facade.

Wraps: MemoryStore, siwe_auth, google_sheets, youtube_skills.
Exposed via Depends() — no module-level globals.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.core.errors import AuthError, NetworkError

if TYPE_CHECKING:
    from app.services.memory_store import MemoryStore

_log = logging.getLogger(__name__)


class InfraServices:
    """Aggregates all infra-domain services. Singleton via get_infra() in deps.py."""

    def __init__(self, memory: MemoryStore) -> None:
        self._memory = memory
        self._google_sheets: Any = None
        self._youtube: Any = None
        self._init_optional_services()

    def _init_optional_services(self) -> None:
        try:
            from app.services.google_sheets import GoogleSheetsService
            self._google_sheets = GoogleSheetsService()
        except (ImportError, OSError, Exception) as exc:
            _log.warning("GoogleSheets unavailable: %s", exc)
            self._google_sheets = None
        try:
            from app.services.youtube_skills import YouTubeSkillsService
            self._youtube = YouTubeSkillsService()
        except (ImportError, OSError, Exception) as exc:
            _log.warning("YouTubeSkills unavailable: %s", exc)
            self._youtube = None

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def health(self) -> dict[str, Any]:
        return {"ok": True, "status": "ok", "service": "Bridge AI OS API"}

    # ------------------------------------------------------------------
    # SIWE Auth
    # ------------------------------------------------------------------

    async def verify_siwe(self, message: str, signature: str) -> dict[str, Any]:
        from app.services.siwe_auth import (
            create_jwt,
            is_nonce_used,
            parse_siwe_message,
            store_nonce_used,
            verify_domain,
            verify_onchain_role,
            verify_signature,
        )
        message = message.strip()
        signature = signature.strip()
        if not message or not signature:
            raise AuthError("message and signature required")

        parsed = parse_siwe_message(message)
        if not parsed:
            raise AuthError("invalid SIWE message format")

        domain, claimed_address, nonce = parsed
        if not verify_domain(domain):
            raise AuthError(f"domain '{domain}' not allowed")

        recovered = verify_signature(message, signature)
        if not recovered or recovered != claimed_address.lower():
            raise AuthError("signature verification failed")

        if await is_nonce_used(self._memory, claimed_address, nonce):
            raise AuthError("nonce already used (replay attack)")

        if not await verify_onchain_role(claimed_address):
            raise AuthError("on-chain role verification failed")

        await store_nonce_used(self._memory, claimed_address, nonce)
        token = create_jwt(claimed_address, authority="economic")
        return {"ok": True, "token": token, "address": claimed_address}

    # ------------------------------------------------------------------
    # Memory store passthrough
    # ------------------------------------------------------------------

    async def mem_get(self, key: str) -> Any:
        return await self._memory.get(key)

    async def mem_set(self, key: str, value: Any) -> bool:
        return await self._memory.set(key, value)

    async def mem_delete(self, key: str) -> bool:
        return await self._memory.delete(key)

    async def mem_get_recent(self, key: str, limit: int = 50) -> list:
        return await self._memory.get_recent(key, limit)

    # ------------------------------------------------------------------
    # Google Sheets
    # ------------------------------------------------------------------

    def google_sheets_available(self) -> bool:
        return self._google_sheets is not None

    async def sheets_read(self, spreadsheet_id: str, range_: str) -> dict[str, Any]:
        if not self._google_sheets:
            raise NetworkError("Google Sheets service unavailable — check credentials")
        return await self._google_sheets.read_spreadsheet(spreadsheet_id, range_)  # type: ignore[no-any-return]

    async def sheets_append(self, spreadsheet_id: str, range_: str, values: list) -> dict[str, Any]:
        if not self._google_sheets:
            raise NetworkError("Google Sheets service unavailable — check credentials")
        return await self._google_sheets.append_spreadsheet(spreadsheet_id, range_, values)  # type: ignore[no-any-return]

    # ------------------------------------------------------------------
    # YouTube Skills
    # ------------------------------------------------------------------

    def youtube_available(self) -> bool:
        return self._youtube is not None and getattr(self._youtube, "available", False)

    async def youtube_search(self, q: str, limit: int = 8) -> dict[str, Any]:
        if not self.youtube_available():
            raise NetworkError("YouTube Skills service unavailable — set YOUTUBE_API_KEY")
        return await self._youtube.search(q, max_results=min(limit, 25))  # type: ignore[no-any-return]

    async def youtube_learn(self, video_id: str) -> dict[str, Any]:
        if not self.youtube_available():
            raise NetworkError("YouTube Skills service unavailable — set YOUTUBE_API_KEY")
        return await self._youtube.learn_from_video(video_id)  # type: ignore[no-any-return]

    # ------------------------------------------------------------------
    # CLI Orchestration Queue
    # ------------------------------------------------------------------

    _QUEUE_KEY = "cli:queue"
    _HISTORY_KEY = "cli:history"

    @staticmethod
    def _cli_enabled() -> tuple[bool, str]:
        import os
        env = (os.getenv("ENV") or os.getenv("NODE_ENV") or "").strip().lower()
        if env == "local":
            return True, "env_local"
        if (os.getenv("BRIDGE_ALLOW_CLI_RUNNER") or "").strip().lower() in ("1", "true", "yes", "on"):
            return True, "allow_flag"
        return False, "disabled"

    async def _load_queue(self) -> list[dict[str, Any]]:
        import json
        raw = await self._memory.get(self._QUEUE_KEY)
        if not raw:
            return []
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
            return data if isinstance(data, list) else []
        except Exception:
            return []

    async def _save_queue(self, q: list[dict[str, Any]]) -> None:
        import json
        await self._memory.set(self._QUEUE_KEY, json.dumps(q))

    def cli_status(self) -> dict[str, Any]:
        import os
        enabled, reason = self._cli_enabled()
        return {
            "ok": True,
            "enabled": enabled,
            "mode": reason,
            "observed_env": {
                "ENV": os.getenv("ENV"),
                "NODE_ENV": os.getenv("NODE_ENV"),
                "BRIDGE_ALLOW_CLI_RUNNER": os.getenv("BRIDGE_ALLOW_CLI_RUNNER"),
            },
        }

    async def cli_enqueue(self, cmd_id: str, args: list[str], created_by: str = "unknown") -> dict[str, Any]:
        import hashlib
        import json
        import time
        enabled, reason = self._cli_enabled()
        if not enabled:
            raise AuthError(f"cli runner disabled ({reason})")
        if not cmd_id:
            from app.core.errors import ValidationError
            raise ValidationError("cmd_id required")
        base = f"{cmd_id}::{json.dumps(args, ensure_ascii=False)}::{int(time.time())}"
        job_id = "job_" + hashlib.sha256(base.encode("utf-8", errors="ignore")).hexdigest()[:16]
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        job: dict[str, Any] = {
            "id": job_id,
            "created_at": now,
            "created_by": created_by,
            "cmd_id": cmd_id,
            "args": args,
            "status": "queued",
            "runner_id": None,
            "started_at": None,
            "finished_at": None,
            "exit_code": None,
            "stdout": None,
            "stderr": None,
        }
        q = await self._load_queue()
        q.append(job)
        if len(q) > 200:
            q = q[-200:]
        await self._save_queue(q)
        return {"ok": True, "job": job}

    async def cli_queue_next(self, runner_id: str = "runner") -> dict[str, Any]:
        import time
        enabled, reason = self._cli_enabled()
        if not enabled:
            raise AuthError(f"cli runner disabled ({reason})")
        q = await self._load_queue()
        for job in q:
            if job.get("status") == "queued":
                job["status"] = "running"
                job["runner_id"] = runner_id
                job["started_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                await self._save_queue(q)
                return {"ok": True, "job": job}
        return {"ok": True, "job": None}

    async def cli_report(self, payload: dict[str, Any]) -> dict[str, Any]:
        import time

        from app.core.errors import NotFoundError
        job_id = (payload.get("id") or "").strip()
        if not job_id:
            from app.core.errors import ValidationError
            raise ValidationError("id required")
        q = await self._load_queue()
        updated = None
        for job in q:
            if job.get("id") == job_id:
                job["status"] = payload.get("status") or job.get("status")
                job["finished_at"] = payload.get("finished_at") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                job["exit_code"] = payload.get("exit_code")
                job["stdout"] = payload.get("stdout")
                job["stderr"] = payload.get("stderr")
                updated = job
                break
        if updated is None:
            raise NotFoundError("job not found")
        await self._save_queue(q)
        await self._memory.append(self._HISTORY_KEY, updated)
        return {"ok": True, "job": updated}

    async def cli_history(self, limit: int = 30) -> dict[str, Any]:
        limit = max(1, min(int(limit), 200))
        items = await self._memory.get_recent(self._HISTORY_KEY, limit)
        return {"ok": True, "count": len(items), "items": list(reversed(items))}

    # ------------------------------------------------------------------
    # Skills (from routes/api.py)
    # ------------------------------------------------------------------

    async def list_skills(self) -> dict[str, Any]:
        skills = await self._memory.get_recent("skills", 200)
        return {"ok": True, "skills": skills, "count": len(skills)}

    async def add_skill(self, skill: dict[str, Any]) -> dict[str, Any]:
        from app.runtime import mission_service
        await mission_service.save_skill(skill)
        return {"ok": True}

    # ------------------------------------------------------------------
    # User settings (from routes/api.py)
    # ------------------------------------------------------------------

    _USER_SETTINGS_PREFIX = "user:settings:"

    async def user_settings_get(self, uid: str) -> dict[str, Any]:
        import json as _json
        key = self._USER_SETTINGS_PREFIX + uid
        raw = await self._memory.get(key)
        if not raw:
            return {"ok": True, "settings": {}}
        try:
            data = _json.loads(raw) if isinstance(raw, str) else raw
            return {"ok": True, "settings": data if isinstance(data, dict) else {}}
        except Exception:
            return {"ok": True, "settings": {}}

    async def user_settings_put(self, uid: str, settings: dict[str, Any]) -> dict[str, Any]:
        import json as _json
        key = self._USER_SETTINGS_PREFIX + uid
        await self._memory.set(key, _json.dumps(settings))
        return {"ok": True, "settings": settings}

    # ------------------------------------------------------------------
    # Health extended (from routes/api.py)
    # ------------------------------------------------------------------

    def health_extended(self) -> dict[str, Any]:
        from app.physics import (
            economic_circuit_breaker_tripped,
            economic_entropy_score,
        )
        from app.physics import (
            telemetry as _t,
        )
        err_rate = 0.0
        total = _t.state_mutation_count + _t.failed_mutation_count
        if total > 0:
            err_rate = _t.failed_mutation_count / total
        silence_dev = abs(_t.silence_rate - 0.5) * 2
        dl = list(_t.decision_latency_ms)
        p95 = sorted(dl)[int(len(dl) * 0.95)] if dl else 0
        latency_factor = 1.0 if p95 <= 100 else max(0, 1.0 - (p95 - 100) / 500)
        circuit_ok = 0.0 if economic_circuit_breaker_tripped() else 1.0
        entropy_ok = 1.0 - min(1.0, economic_entropy_score())
        health_score = (1 - err_rate) * (1 - silence_dev) * latency_factor * circuit_ok * entropy_ok
        return {
            "ok": health_score >= 0.5,
            "health_score": round(health_score, 4),
            "components": {
                "error_rate": round(err_rate, 4),
                "silence_spike_deviation": round(silence_dev, 4),
                "latency_factor": round(latency_factor, 4),
                "circuit_breaker_ok": circuit_ok,
                "entropy_ok": round(entropy_ok, 4),
            },
        }

    # ------------------------------------------------------------------
    # Sensors (from routes/api.py)
    # ------------------------------------------------------------------

    async def sensors_wifi_post(self, payload: dict[str, Any]) -> dict[str, Any]:
        from app.cortex import set_sensor_wifi
        await set_sensor_wifi(self._memory, payload)
        return {"ok": True}

    async def sensors_wifi_get(self) -> dict[str, Any]:
        from app.cortex import get_sensor_wifi
        out = await get_sensor_wifi(self._memory)
        return {"ok": True, "wifi": out}

    _MOUSE_SESSION_KEY = "sensor:mouse:session"
    _MOUSE_MOVES_PER_TASK = 12
    _MOUSE_BRDG_PER_TASK = 0.5

    async def sensors_mouse_post(self, payload: dict[str, Any]) -> dict[str, Any]:
        import json as _json

        from app.cortex import set_sensor_mouse
        await set_sensor_mouse(self._memory, payload)
        earned: float = 0.0
        task_created: bool = False
        if payload.get("moved"):
            raw = await self._memory.get(self._MOUSE_SESSION_KEY)
            try:
                session: dict = _json.loads(raw) if isinstance(raw, str) and raw else {}
            except Exception:
                session = {}
            active_count = int(session.get("active_count", 0)) + 1
            total_earned = float(session.get("total_earned", 0.0))
            if active_count >= self._MOUSE_MOVES_PER_TASK:
                from app.runtime import marketplace_service, revenue_service
                task = marketplace_service.add_task({
                    "title": "Mouse Activity — Human Presence",
                    "description": f"Passive income: user active for ~{self._MOUSE_MOVES_PER_TASK * 5}s",
                    "reward": self._MOUSE_BRDG_PER_TASK,
                    "type": "sensor",
                    "source": payload.get("source", "mouse-tracker"),
                })
                marketplace_service.accept_task(task["id"], "user")
                marketplace_service.complete_task(task["id"])
                revenue_service.collect(self._MOUSE_BRDG_PER_TASK, source="sensor", method="sensor")
                earned = self._MOUSE_BRDG_PER_TASK
                total_earned += earned
                active_count = 0
                task_created = True
            session["active_count"] = active_count
            session["total_earned"] = total_earned
            await self._memory.set(self._MOUSE_SESSION_KEY, _json.dumps(session))
        return {"ok": True, "earned": earned, "task_created": task_created}

    async def sensors_mouse_get(self) -> dict[str, Any]:
        import json as _json

        from app.cortex import get_sensor_mouse
        out = await get_sensor_mouse(self._memory)
        raw = await self._memory.get(self._MOUSE_SESSION_KEY)
        try:
            session: dict = _json.loads(raw) if isinstance(raw, str) and raw else {}
        except Exception:
            session = {}
        return {"ok": True, "mouse": out, "session": session}

    # ------------------------------------------------------------------
    # Live map / report (from routes/api.py)
    # ------------------------------------------------------------------

    async def live_map(self) -> dict[str, Any]:
        import json as _json
        import time
        from pathlib import Path

        from app.cortex import (
            CAPABILITIES,
            capability_enabled,
            get_boots_log,
            get_current_run,
            get_runs_log,
            get_sensor_mouse,
            get_sensor_wifi,
        )
        from app.physics import telemetry
        from app.runtime import twins_competition
        repo_root = Path(__file__).resolve().parents[4]
        cfg = None
        try:
            config_path = repo_root / "config" / "bridge-wall.config.json"
            if config_path.exists():
                cfg = _json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            pass
        state_version = await self._memory.get("state:version") or 0
        state_hash = await self._memory.get("state:hash") or ""
        boots = await get_boots_log(self._memory)
        runs = await get_runs_log(self._memory)
        current_run = await get_current_run(self._memory)
        twins = twins_competition.list_twins()
        leaderboard = twins_competition.get_leaderboard()
        caps = {k: capability_enabled(k) for k in (CAPABILITIES or {})}
        telem = telemetry.to_dict() if hasattr(telemetry, "to_dict") else {}
        services = []
        if cfg and isinstance(cfg.get("services"), dict):
            for name, svc in cfg["services"].items():
                port = svc.get("port") or svc.get("hostPort")
                label = svc.get("label") or name
                services.append({"id": name, "label": label, "port": port})
        wifi_sensor = await get_sensor_wifi(self._memory)
        mouse_sensor = await get_sensor_mouse(self._memory)
        return {
            "ok": True,
            "ts": time.time(),
            "pboots": boots[-20:],
            "runbs": runs[-20:],
            "current_run": current_run,
            "state_version": state_version,
            "state_hash": state_hash,
            "twins": twins,
            "leaderboard": leaderboard,
            "capabilities": caps,
            "telemetry": telem,
            "services": services,
            "config_loaded": cfg is not None,
            "sensors": {"wifi": wifi_sensor, "mouse": mouse_sensor},
        }

    # ------------------------------------------------------------------
    # Orchestrate + Wiki (from routes/api.py)
    # ------------------------------------------------------------------

    def orchestrate_directives(self) -> dict[str, Any]:
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[4]
        directives = [
            {"id": "sync_twins_wiki", "label": "Sync twins and wiki", "script": ".\\scripts\\sync-twins-wiki.ps1", "cwd": str(repo_root), "description": "Sync all digital twins and versioned artifacts."},
            {"id": "audit", "label": "Full audit", "script": ".\\audit-wall.ps1", "cwd": str(repo_root), "description": "Run audit (keys, ports, DNS, drives)."},
            {"id": "refresh_wallpaper", "label": "Refresh wallpaper", "script": ".\\update.ps1", "cwd": str(repo_root), "description": "Update digital twin wallpaper."},
            {"id": "port_list", "label": "Port status", "script": ".\\scripts\\port-handler.ps1 list", "cwd": str(repo_root), "description": "List port status."},
        ]
        return {"ok": True, "directives": directives}

    async def wiki_registry(self) -> dict[str, Any]:
        import json as _json
        from pathlib import Path

        from app.core.errors import NetworkError
        repo_root = Path(__file__).resolve().parents[4]
        registry_path = repo_root / "data" / "twin-registry.json"
        if not registry_path.exists():
            raise NetworkError("Registry not found. Run .\\scripts\\sync-twins-wiki.ps1 first.")
        data = _json.loads(registry_path.read_text(encoding="utf-8"))
        return {"ok": True, "registry": data}
