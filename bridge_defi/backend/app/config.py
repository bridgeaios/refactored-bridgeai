"""Application configuration."""
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/bridgedefi"

    # JWT
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:5173/auth/callback"

    # Rate Limiting (per tier)
    rate_limit_basic: int = 60
    rate_limit_silver: int = 120
    rate_limit_gold: int = 300
    rate_limit_platinum: int = 0  # Unlimited

    # Fee Rates (by tier)
    fee_basic: float = 0.005
    fee_silver: float = 0.004
    fee_gold: float = 0.0025
    fee_platinum: float = 0.001

    # Transaction Limits (daily)
    daily_limit_basic: float = 1000.0
    daily_limit_silver: float = 10000.0
    daily_limit_gold: float = 50000.0
    daily_limit_platinum: float = 0.0  # Unlimited

    # Lending
    min_collateral_ratio: float = 1.10
    max_collateral_ratio: float = 1.50
    liquidation_bonus: float = 0.05

    # Staking APY (by lock period)
    apy_30_days: float = 0.05
    apy_60_days: float = 0.08
    apy_90_days: float = 0.12
    apy_180_days: float = 0.20

    # DEX
    default_slippage: float = 0.005

    # Treasury Distribution
    treasury_ubi_percent: float = 0.40
    treasury_ops_percent: float = 0.20
    treasury_founder_percent: float = 0.10
    treasury_reserve_percent: float = 0.30

    # Payment Rails
    paystack_secret_key: str = ""
    paypal_client_id: str = ""
    paypal_client_secret: str = ""

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
