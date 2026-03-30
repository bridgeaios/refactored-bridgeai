"""
Google OAuth 2.0 — exchange authorization code for user info.
"""
from __future__ import annotations

import os
from typing import Any

import httpx

_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


class GoogleOAuthError(Exception):
    pass


async def exchange_code(code: str, redirect_uri: str) -> dict[str, Any]:
    """Exchange authorization code for Google user info dict."""
    if not _CLIENT_ID or not _CLIENT_SECRET:
        raise GoogleOAuthError("GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET not set")

    async with httpx.AsyncClient(timeout=10) as client:
        # Step 1: get tokens
        token_resp = await client.post(
            _TOKEN_URL,
            data={
                "code": code,
                "client_id": _CLIENT_ID,
                "client_secret": _CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if token_resp.status_code != 200:
            raise GoogleOAuthError(f"token exchange failed: {token_resp.text}")
        tokens = token_resp.json()
        access_token = tokens.get("access_token")
        if not access_token:
            raise GoogleOAuthError("no access_token in response")

        # Step 2: fetch user info
        user_resp = await client.get(
            _USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if user_resp.status_code != 200:
            raise GoogleOAuthError(f"userinfo failed: {user_resp.text}")
        return user_resp.json()  # type: ignore[no-any-return]
