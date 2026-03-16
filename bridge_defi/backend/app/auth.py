"""Authentication module with JWT and Google OAuth."""
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from app.models.models import RefreshToken, User, UserTier
from app.models.schemas import TokenResponse


def generate_random_token(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    settings = get_settings()
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        return payload
    except JWTError:
        return None


async def authenticate_google(code: str, db: AsyncSession) -> tuple[User, TokenResponse]:
    settings = get_settings()

    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        token_response.raise_for_status()
        tokens = token_response.json()

        access_token = tokens["access_token"]
        userinfo_response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        userinfo_response.raise_for_status()
        userinfo = userinfo_response.json()

    google_id = userinfo["id"]
    email = userinfo["email"]
    name = userinfo.get("name")

    result = await db.execute(
        select(User).where(User.google_id == google_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            google_id=google_id,
            email=email,
            name=name,
            tier=UserTier.BASIC,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    access_token_jwt = create_access_token({"sub": str(user.id)})
    refresh_token_jwt = create_refresh_token({"sub": str(user.id)})

    refresh_token = RefreshToken(
        user_id=user.id,
        token=refresh_token_jwt,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(refresh_token)
    await db.commit()

    return user, TokenResponse(
        access_token=access_token_jwt,
        refresh_token=refresh_token_jwt,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


async def refresh_access_token(
    refresh_token: str, db: AsyncSession
) -> Optional[TokenResponse]:
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        return None

    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token == refresh_token,
            RefreshToken.is_revoked == False,
        )
    )
    stored_token = result.scalar_one_or_none()
    if not stored_token or stored_token.expires_at < datetime.now(timezone.utc):
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        return None

    access_token_jwt = create_access_token({"sub": str(user.id)})
    new_refresh_token_jwt = create_refresh_token({"sub": str(user.id)})

    stored_token.is_revoked = True
    new_refresh_token = RefreshToken(
        user_id=user.id,
        token=new_refresh_token_jwt,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(new_refresh_token)
    await db.commit()

    settings = get_settings()
    return TokenResponse(
        access_token=access_token_jwt,
        refresh_token=new_refresh_token_jwt,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


async def revoke_token(token: str, db: AsyncSession) -> bool:
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == token)
    )
    stored_token = result.scalar_one_or_none()
    if stored_token:
        stored_token.is_revoked = True
        await db.commit()
        return True
    return False


def get_tier_limits(tier: UserTier) -> dict:
    settings = get_settings()
    limits = {
        UserTier.BASIC: {
            "rate_limit": settings.rate_limit_basic,
            "fee": settings.fee_basic,
            "daily_limit": settings.daily_limit_basic,
        },
        UserTier.SILVER: {
            "rate_limit": settings.rate_limit_silver,
            "fee": settings.fee_silver,
            "daily_limit": settings.daily_limit_silver,
        },
        UserTier.GOLD: {
            "rate_limit": settings.rate_limit_gold,
            "fee": settings.fee_gold,
            "daily_limit": settings.daily_limit_gold,
        },
        UserTier.PLATINUM: {
            "rate_limit": settings.rate_limit_platinum,
            "fee": settings.fee_platinum,
            "daily_limit": settings.daily_limit_platinum,
        },
    }
    return limits[tier]
