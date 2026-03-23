"""
Infra domain service facade.
"""
from __future__ import annotations

import logging
from typing import Any, Optional, TYPE_CHECKING

from app.core.errors import AuthError, NetworkError
from app.services.memory_store import MemoryStore

if TYPE_CHECKING:
    pass

_log = logging.getLogger(__name__)


class InfraServices:
    """Aggregates infra-domain helpers."""

    def __init__(self, memory: MemoryStore) -> None:
        self._memory = memory
        self._google_sheets: Any = None
        self._youtube: Any = None
        self._init_optional_services()

    def _init_optional_services(self) -> None:
        try:
            from app.services.google_sheets import GoogleSheetsService

            self._google_sheets = GoogleSheetsService()
        except (ImportError, OSError) as exc:
            _log.warning("GoogleSheets unavailable: %s — continuing without it", exc)
            self._google_sheets = None
        try:
            from app.services.youtube_skills import YouTubeSkillsService

            self._youtube = YouTubeSkillsService()
        except (ImportError, OSError) as exc:
            _log.warning("YouTubeSkills unavailable: %s — continuing without it", exc)
            self._youtube = None

    def health(self) -> dict[str, Any]:
        return {"ok": True, "status": "ok", "service": "bridge-api"}

    async def verify_siwe(
        self,
        message: str,
        signature: str,
        address: Optional[str] = None,
    ) -> dict[str, Any]:
        from app.cortex import wrap_response
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
            raise AuthError("invalid message format")

        domain, claimed_address, nonce = parsed
        if address is not None and address.lower() != claimed_address.lower():
            raise AuthError("address does not match message")

        if not verify_domain(domain):
            raise AuthError("domain not allowed")

        recovered = verify_signature(message, signature)
        if not recovered or recovered != claimed_address.lower():
            raise AuthError("signature verification failed")

        if await is_nonce_used(self._memory, claimed_address, nonce):
            raise AuthError("nonce already used (replay)")

        if not await verify_onchain_role(claimed_address):
            raise AuthError("on-chain role verification failed")

        await store_nonce_used(self._memory, claimed_address, nonce)

        token = create_jwt(claimed_address, authority="economic")
        return wrap_response(
            {"token": token, "address": claimed_address, "auth": "economic"},
            ok=True,
        )

    async def mem_get(self, key: str) -> Any:
        return await self._memory.get(key)

    async def mem_set(self, key: str, value: Any) -> bool:
        import json

        payload = value if isinstance(value, str) else json.dumps(value)
        return await self._memory.set(key, payload)

    async def mem_delete(self, key: str) -> bool:
        await self._memory.set(key, None)
        return True

    async def mem_get_recent(self, key: str, limit: int = 50) -> list:
        return await self._memory.get_recent(key, limit)

    def google_sheets_available(self) -> bool:
        return self._google_sheets is not None

    async def sheets_read(self, spreadsheet_id: str, range_: str) -> dict[str, Any]:
        if not self._google_sheets:
            raise NetworkError("Google Sheets service unavailable — check credentials")
        return await self._google_sheets.read(spreadsheet_id, range_)

    async def sheets_append(self, spreadsheet_id: str, range_: str, values: list) -> dict[str, Any]:
        if not self._google_sheets:
            raise NetworkError("Google Sheets service unavailable — check credentials")
        return await self._google_sheets.append(spreadsheet_id, range_, values)

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
