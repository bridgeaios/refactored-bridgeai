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
        return {"ok": True, "status": "ok", "service": "bridge-api"}

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
        return await self._google_sheets.read_spreadsheet(spreadsheet_id, range_)

    async def sheets_append(self, spreadsheet_id: str, range_: str, values: list) -> dict[str, Any]:
        if not self._google_sheets:
            raise NetworkError("Google Sheets service unavailable — check credentials")
        return await self._google_sheets.append_spreadsheet(spreadsheet_id, range_, values)

    # ------------------------------------------------------------------
    # YouTube Skills
    # ------------------------------------------------------------------

    def youtube_available(self) -> bool:
        return self._youtube is not None and getattr(self._youtube, "available", False)

    async def youtube_search(self, q: str, limit: int = 8) -> dict[str, Any]:
        if not self.youtube_available():
            raise NetworkError("YouTube Skills service unavailable — set YOUTUBE_API_KEY")
        return await self._youtube.search(q, max_results=min(limit, 25))

    async def youtube_learn(self, video_id: str) -> dict[str, Any]:
        if not self.youtube_available():
            raise NetworkError("YouTube Skills service unavailable — set YOUTUBE_API_KEY")
        return await self._youtube.learn_from_video(video_id)

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
        import hashlib, json, time
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
