"""
001_unified_schema.py — Unified PostgreSQL schema migration.

Merges:
  - Site B (BridgeLiveWall): DeFi ORM tables, CRM/billing/economy Pydantic→SQL,
    governance, twins, network, infra
  - Site A (BRIDGE_AI_OS / bridgeos): users, referrals, commissions, payments,
    api_keys, sessions, modules, runtime services, training, esim, tts, dex trades

All statements use IF NOT EXISTS / ON CONFLICT so the migration is fully idempotent.

Usage:
    import asyncio, asyncpg
    from migrations.001_unified_schema import run_migration
    asyncio.run(run_migration("postgresql://user:pass@host/db"))
"""
from __future__ import annotations

# Each element is a SQL statement executed in order.
STATEMENTS: list[str] = []

# ============================================================================
# Helper to register SQL
# ============================================================================
def _s(sql: str) -> None:
    STATEMENTS.append(sql.strip())


# ============================================================================
# 0. Extensions
# ============================================================================
_s("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
_s("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")

# ============================================================================
# 1. Enum types
# ============================================================================
_s("""
DO $$ BEGIN
    CREATE TYPE user_tier AS ENUM ('basic','silver','gold','platinum');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
""")
_s("""
DO $$ BEGIN
    CREATE TYPE loan_status AS ENUM ('open','repaid','liquidated','defaulted');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
""")
_s("""
DO $$ BEGIN
    CREATE TYPE stake_status AS ENUM ('active','unlocked','withdrawn');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
""")
_s("""
DO $$ BEGIN
    CREATE TYPE yield_status AS ENUM ('active','withdrawn');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
""")
_s("""
DO $$ BEGIN
    CREATE TYPE subscription_status AS ENUM ('active','cancelled','expired','trialing');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
""")
_s("""
DO $$ BEGIN
    CREATE TYPE subscription_plan AS ENUM ('starter','growth');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
""")
_s("""
DO $$ BEGIN
    CREATE TYPE crm_stage AS ENUM ('new','qualified','proposal','negotiation','won','lost');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
""")
_s("""
DO $$ BEGIN
    CREATE TYPE invoice_status AS ENUM ('draft','sent','paid','overdue','cancelled');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
""")
_s("""
DO $$ BEGIN
    CREATE TYPE runtime_svc_state AS ENUM (
        'stopped','starting','running','unhealthy','failed','failed_locked'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
""")
_s("""
DO $$ BEGIN
    CREATE TYPE governance_vote AS ENUM ('yes','no','abstain');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
""")

# ============================================================================
# 2. Site A — bridgeos core tables (from schema.sql)
# ============================================================================
_s("""
CREATE TABLE IF NOT EXISTS users (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email          TEXT UNIQUE NOT NULL,
    password_hash  TEXT NOT NULL DEFAULT '',
    referral_code  TEXT UNIQUE NOT NULL,
    referred_by    TEXT,
    tier           TEXT DEFAULT 'free',
    commission_rate NUMERIC(5,4) DEFAULT 0.20,
    is_active      BOOLEAN DEFAULT TRUE,
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    updated_at     TIMESTAMPTZ DEFAULT NOW()
);
""")

_s("""
CREATE TABLE IF NOT EXISTS referrals (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    referrer_code   TEXT NOT NULL,
    referred_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    source          TEXT DEFAULT 'direct',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
""")

_s("""
CREATE TABLE IF NOT EXISTS commissions (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id       UUID REFERENCES users(id) ON DELETE CASCADE,
    amount        NUMERIC(18,6) NOT NULL,
    source_user   UUID REFERENCES users(id) ON DELETE SET NULL,
    status        TEXT DEFAULT 'pending',
    created_at    TIMESTAMPTZ DEFAULT NOW()
);
""")

_s("""
CREATE TABLE IF NOT EXISTS payments (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    stripe_session  TEXT,
    amount          NUMERIC(18,6) NOT NULL,
    currency        TEXT DEFAULT 'usd',
    status          TEXT DEFAULT 'pending',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
""")

_s("""
CREATE TABLE IF NOT EXISTS api_keys (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key_text    TEXT UNIQUE NOT NULL,
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    tier        TEXT DEFAULT 'free',
    expires_at  TIMESTAMPTZ,
    usage_count INT DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
""")

_s("""
CREATE TABLE IF NOT EXISTS sessions (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    token       TEXT UNIQUE NOT NULL,
    expires_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
""")

_s("""
CREATE TABLE IF NOT EXISTS modules (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        TEXT NOT NULL,
    description TEXT,
    price       NUMERIC(12,2) NOT NULL,
    category    TEXT,
    version     TEXT DEFAULT '1.0.0',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
""")

# ============================================================================
# 3. Site B — DeFi tables (from SQLAlchemy ORM models)
# ============================================================================
_s("""
CREATE TABLE IF NOT EXISTS defi_users (
    id                    SERIAL PRIMARY KEY,
    google_sub            VARCHAR(128) UNIQUE NOT NULL,
    email                 VARCHAR(255) UNIQUE NOT NULL,
    name                  VARCHAR(255),
    picture               VARCHAR(512),
    tier                  user_tier DEFAULT 'basic' NOT NULL,
    is_active             BOOLEAN DEFAULT TRUE NOT NULL,
    geo_country           VARCHAR(8),
    native_token_holdings DOUBLE PRECISION DEFAULT 0.0 NOT NULL,
    voucher_credits       DOUBLE PRECISION DEFAULT 0.0 NOT NULL,
    total_volume_usd      DOUBLE PRECISION DEFAULT 0.0 NOT NULL,
    created_at            TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at            TIMESTAMPTZ DEFAULT NOW() NOT NULL
);
""")

_s("""
CREATE TABLE IF NOT EXISTS defi_refresh_tokens (
    id          SERIAL PRIMARY KEY,
    user_id     INT NOT NULL REFERENCES defi_users(id) ON DELETE CASCADE,
    token_hash  VARCHAR(128) UNIQUE NOT NULL,
    family      VARCHAR(64) NOT NULL,
    is_revoked  BOOLEAN DEFAULT FALSE NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    replaced_by VARCHAR(128)
);
""")

_s("""
CREATE TABLE IF NOT EXISTS defi_loans (
    id                    SERIAL PRIMARY KEY,
    borrower_id           INT NOT NULL REFERENCES defi_users(id) ON DELETE CASCADE,
    principal_usd         DOUBLE PRECISION NOT NULL,
    collateral_usd        DOUBLE PRECISION NOT NULL,
    collateral_ratio      DOUBLE PRECISION NOT NULL,
    collateral_token      VARCHAR(16) DEFAULT 'ETH' NOT NULL,
    collateral_amount     DOUBLE PRECISION NOT NULL,
    interest_rate_annual  DOUBLE PRECISION NOT NULL,
    compound_frequency    INT DEFAULT 365 NOT NULL,
    origination_fee_usd   DOUBLE PRECISION DEFAULT 0.0 NOT NULL,
    outstanding_principal DOUBLE PRECISION NOT NULL,
    accrued_interest      DOUBLE PRECISION DEFAULT 0.0 NOT NULL,
    liquidation_bonus     DOUBLE PRECISION DEFAULT 0.05 NOT NULL,
    liquidation_threshold DOUBLE PRECISION DEFAULT 1.1 NOT NULL,
    status                loan_status DEFAULT 'open' NOT NULL,
    duration_days         INT DEFAULT 30 NOT NULL,
    opened_at             TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    due_at                TIMESTAMPTZ,
    closed_at             TIMESTAMPTZ,
    last_compounded_at    TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    meta                  JSONB DEFAULT '{}'::jsonb NOT NULL
);
""")

_s("""
CREATE TABLE IF NOT EXISTS defi_loan_payments (
    id                SERIAL PRIMARY KEY,
    loan_id           INT NOT NULL REFERENCES defi_loans(id) ON DELETE CASCADE,
    amount_usd        DOUBLE PRECISION NOT NULL,
    principal_portion DOUBLE PRECISION DEFAULT 0.0 NOT NULL,
    interest_portion  DOUBLE PRECISION DEFAULT 0.0 NOT NULL,
    paid_at           TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    tx_hash           VARCHAR(128)
);
""")

_s("""
CREATE TABLE IF NOT EXISTS defi_stakes (
    id              SERIAL PRIMARY KEY,
    user_id         INT NOT NULL REFERENCES defi_users(id) ON DELETE CASCADE,
    token           VARCHAR(16) DEFAULT 'BRDG' NOT NULL,
    amount          DOUBLE PRECISION NOT NULL,
    lock_days       INT NOT NULL,
    apy             DOUBLE PRECISION NOT NULL,
    rewards_earned  DOUBLE PRECISION DEFAULT 0.0 NOT NULL,
    status          stake_status DEFAULT 'active' NOT NULL,
    staked_at       TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    unlock_at       TIMESTAMPTZ NOT NULL,
    withdrawn_at    TIMESTAMPTZ,
    last_reward_at  TIMESTAMPTZ DEFAULT NOW() NOT NULL
);
""")

_s("""
CREATE TABLE IF NOT EXISTS defi_yield_positions (
    id                        SERIAL PRIMARY KEY,
    user_id                   INT NOT NULL REFERENCES defi_users(id) ON DELETE CASCADE,
    protocol                  VARCHAR(64) NOT NULL,
    pool_id                   VARCHAR(128) NOT NULL,
    token_a                   VARCHAR(16) NOT NULL,
    token_b                   VARCHAR(16) NOT NULL,
    liquidity_usd             DOUBLE PRECISION NOT NULL,
    shares                    DOUBLE PRECISION NOT NULL,
    apy                       DOUBLE PRECISION NOT NULL,
    pending_rewards_usd       DOUBLE PRECISION DEFAULT 0.0 NOT NULL,
    total_rewards_claimed_usd DOUBLE PRECISION DEFAULT 0.0 NOT NULL,
    auto_compound             BOOLEAN DEFAULT TRUE NOT NULL,
    last_compounded_at        TIMESTAMPTZ,
    status                    yield_status DEFAULT 'active' NOT NULL,
    entered_at                TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    exited_at                 TIMESTAMPTZ
);
""")

_s("""
CREATE TABLE IF NOT EXISTS defi_swaps (
    id            SERIAL PRIMARY KEY,
    user_id       INT NOT NULL REFERENCES defi_users(id) ON DELETE CASCADE,
    token_in      VARCHAR(16) NOT NULL,
    token_out     VARCHAR(16) NOT NULL,
    amount_in     DOUBLE PRECISION NOT NULL,
    amount_out    DOUBLE PRECISION NOT NULL,
    price_usd_in  DOUBLE PRECISION NOT NULL,
    price_usd_out DOUBLE PRECISION NOT NULL,
    protocol      VARCHAR(64) NOT NULL,
    slippage_pct  DOUBLE PRECISION NOT NULL,
    fee_usd       DOUBLE PRECISION NOT NULL,
    fee_pct       DOUBLE PRECISION NOT NULL,
    tx_hash       VARCHAR(128),
    chain_id      INT DEFAULT 1 NOT NULL,
    executed_at   TIMESTAMPTZ DEFAULT NOW() NOT NULL
);
""")

_s("""
CREATE TABLE IF NOT EXISTS defi_dex_prices (
    id               SERIAL PRIMARY KEY,
    token            VARCHAR(16) NOT NULL,
    price_usd        DOUBLE PRECISION NOT NULL,
    source           VARCHAR(64) DEFAULT 'coingecko' NOT NULL,
    daily_change_pct DOUBLE PRECISION,
    daily_volume_usd DOUBLE PRECISION,
    fetched_at       TIMESTAMPTZ DEFAULT NOW() NOT NULL
);
""")

_s("""
CREATE TABLE IF NOT EXISTS defi_tax_lots (
    id              SERIAL PRIMARY KEY,
    user_id         INT NOT NULL REFERENCES defi_users(id) ON DELETE CASCADE,
    token           VARCHAR(16) NOT NULL,
    amount          DOUBLE PRECISION NOT NULL,
    cost_basis_usd  DOUBLE PRECISION NOT NULL,
    acquired_at     TIMESTAMPTZ NOT NULL,
    disposed_amount DOUBLE PRECISION DEFAULT 0.0 NOT NULL,
    disposed_at     TIMESTAMPTZ,
    proceeds_usd    DOUBLE PRECISION,
    gain_usd        DOUBLE PRECISION,
    source          VARCHAR(32) DEFAULT 'swap' NOT NULL
);
""")

_s("""
CREATE TABLE IF NOT EXISTS defi_subscriptions (
    id              SERIAL PRIMARY KEY,
    user_id         INT NOT NULL REFERENCES defi_users(id) ON DELETE CASCADE UNIQUE,
    plan            subscription_plan NOT NULL,
    status          subscription_status DEFAULT 'active' NOT NULL,
    billing_cycle   VARCHAR(16) DEFAULT 'monthly' NOT NULL,
    price_usd       DOUBLE PRECISION NOT NULL,
    discount_pct    DOUBLE PRECISION DEFAULT 0.0 NOT NULL,
    payment_rail    VARCHAR(32) DEFAULT 'paystack' NOT NULL,
    external_ref    VARCHAR(128),
    started_at      TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    next_billing_at TIMESTAMPTZ,
    cancelled_at    TIMESTAMPTZ,
    meta            JSONB DEFAULT '{}'::jsonb NOT NULL
);
""")

_s("""
CREATE TABLE IF NOT EXISTS defi_wallet_sessions (
    id              SERIAL PRIMARY KEY,
    user_id         INT NOT NULL REFERENCES defi_users(id) ON DELETE CASCADE,
    wallet_type     VARCHAR(32) NOT NULL,
    address         VARCHAR(64) NOT NULL,
    chain_id        INT DEFAULT 1 NOT NULL,
    is_active       BOOLEAN DEFAULT TRUE NOT NULL,
    connected_at    TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    disconnected_at TIMESTAMPTZ
);
""")

_s("""
CREATE TABLE IF NOT EXISTS defi_portfolio_snapshots (
    id              SERIAL PRIMARY KEY,
    user_id         INT NOT NULL REFERENCES defi_users(id) ON DELETE CASCADE,
    total_value_usd DOUBLE PRECISION NOT NULL,
    holdings        JSONB DEFAULT '{}'::jsonb NOT NULL,
    prices          JSONB DEFAULT '{}'::jsonb NOT NULL,
    risk_score      DOUBLE PRECISION,
    var_1d_usd      DOUBLE PRECISION,
    snapped_at      TIMESTAMPTZ DEFAULT NOW() NOT NULL
);
""")

# ============================================================================
# 4. CRM domain tables (from Pydantic schemas)
# ============================================================================
_s("""
CREATE TABLE IF NOT EXISTS crm_leads (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           TEXT NOT NULL,
    company         TEXT DEFAULT '',
    name            TEXT DEFAULT '',
    phone           TEXT DEFAULT '',
    source          TEXT DEFAULT 'scraper',
    stage           crm_stage DEFAULT 'new' NOT NULL,
    score           DOUBLE PRECISION DEFAULT 0.0,
    industry        TEXT DEFAULT 'unknown',
    size_estimate   TEXT DEFAULT 'unknown',
    pain_points     JSONB DEFAULT '[]'::jsonb,
    template_type   TEXT DEFAULT 'generic',
    osint_profile   JSONB DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
""")

_s("""
CREATE TABLE IF NOT EXISTS crm_activities (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id     UUID NOT NULL REFERENCES crm_leads(id) ON DELETE CASCADE,
    type        TEXT NOT NULL,
    text        TEXT DEFAULT '',
    meta        JSONB DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
""")

_s("""
CREATE TABLE IF NOT EXISTS crm_deals (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id     UUID NOT NULL REFERENCES crm_leads(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    value       NUMERIC(18,2) DEFAULT 0.0,
    currency    TEXT DEFAULT 'ZAR',
    stage       crm_stage DEFAULT 'new' NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);
""")

# ============================================================================
# 5. Billing / Invoicing domain
# ============================================================================
_s("""
CREATE TABLE IF NOT EXISTS invoices (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    invoice_number  TEXT UNIQUE NOT NULL,
    lead_id         UUID REFERENCES crm_leads(id) ON DELETE SET NULL,
    deal_id         UUID REFERENCES crm_deals(id) ON DELETE SET NULL,
    client_email    TEXT NOT NULL,
    client_name     TEXT DEFAULT '',
    client_company  TEXT DEFAULT '',
    items           JSONB NOT NULL DEFAULT '[]'::jsonb,
    subtotal        NUMERIC(18,2) NOT NULL DEFAULT 0,
    tax_rate        NUMERIC(5,4) DEFAULT 0.15,
    tax             NUMERIC(18,2) NOT NULL DEFAULT 0,
    total           NUMERIC(18,2) NOT NULL DEFAULT 0,
    currency        TEXT DEFAULT 'ZAR',
    status          invoice_status DEFAULT 'draft' NOT NULL,
    notes           TEXT DEFAULT '',
    issued_at       TIMESTAMPTZ DEFAULT NOW(),
    due_date        TIMESTAMPTZ,
    paid_at         TIMESTAMPTZ,
    payment_method  TEXT
);
""")

# ============================================================================
# 6. Economy domain (treasury, marketplace tasks)
# ============================================================================
_s("""
CREATE TABLE IF NOT EXISTS treasury_ledger (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tx_id           TEXT UNIQUE NOT NULL,
    amount          NUMERIC(18,6) NOT NULL,
    currency        TEXT DEFAULT 'BRDG',
    source_project  TEXT DEFAULT 'bridge',
    method          TEXT DEFAULT 'internal',
    type            TEXT DEFAULT 'manual',
    splits          JSONB DEFAULT '{}'::jsonb,
    meta            JSONB DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
""")

_s("""
CREATE TABLE IF NOT EXISTS marketplace_tasks (
    id              SERIAL PRIMARY KEY,
    title           TEXT NOT NULL,
    value           NUMERIC(18,6) NOT NULL,
    tags            JSONB DEFAULT '[]'::jsonb,
    status          TEXT DEFAULT 'open',
    posted_by       TEXT DEFAULT 'system',
    claimed_by      TEXT,
    twin_id         TEXT DEFAULT 'system',
    priority_score  DOUBLE PRECISION DEFAULT 0.0,
    result          TEXT,
    meta            JSONB DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);
""")

# ============================================================================
# 7. Governance domain
# ============================================================================
_s("""
CREATE TABLE IF NOT EXISTS governance_proposals (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title           TEXT NOT NULL,
    description     TEXT DEFAULT '',
    proposer_id     TEXT NOT NULL,
    payload         JSONB DEFAULT '{}'::jsonb,
    status          TEXT DEFAULT 'open',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    closed_at       TIMESTAMPTZ
);
""")

_s("""
CREATE TABLE IF NOT EXISTS governance_votes (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    proposal_id     UUID NOT NULL REFERENCES governance_proposals(id) ON DELETE CASCADE,
    voter_id        TEXT NOT NULL,
    vote            governance_vote NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(proposal_id, voter_id)
);
""")

_s("""
CREATE TABLE IF NOT EXISTS agent_reputation (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id        TEXT UNIQUE NOT NULL,
    score           DOUBLE PRECISION DEFAULT 0.0,
    total_tasks     INT DEFAULT 0,
    successful_tasks INT DEFAULT 0,
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
""")

# ============================================================================
# 8. Twins domain
# ============================================================================
_s("""
CREATE TABLE IF NOT EXISTS twins (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    twin_id         TEXT UNIQUE NOT NULL,
    name            TEXT,
    status          TEXT DEFAULT 'active',
    capabilities    JSONB DEFAULT '[]'::jsonb,
    emotion_state   TEXT DEFAULT 'neutral',
    emotion_intensity DOUBLE PRECISION DEFAULT 0.5,
    meta            JSONB DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
""")

# ============================================================================
# 9. Network / swarm domain
# ============================================================================
_s("""
CREATE TABLE IF NOT EXISTS network_nodes (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    node_id         TEXT UNIQUE NOT NULL,
    url             TEXT NOT NULL,
    capabilities    JSONB DEFAULT '[]'::jsonb,
    status          TEXT DEFAULT 'active',
    meta            JSONB DEFAULT '{}'::jsonb,
    last_heartbeat  TIMESTAMPTZ DEFAULT NOW(),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
""")

_s("""
CREATE TABLE IF NOT EXISTS network_projects (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            TEXT UNIQUE NOT NULL,
    url             TEXT,
    meta            JSONB DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
""")

# ============================================================================
# 10. Site A unique — Runtime services registry
# ============================================================================
_s("""
CREATE TABLE IF NOT EXISTS runtime_services (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service_name    TEXT UNIQUE NOT NULL,
    command         TEXT NOT NULL,
    port            INT,
    state           runtime_svc_state DEFAULT 'stopped' NOT NULL,
    pid             INT,
    restart_count   INT DEFAULT 0,
    health_endpoint TEXT,
    depends_on      JSONB DEFAULT '[]'::jsonb,
    meta            JSONB DEFAULT '{}'::jsonb,
    started_at      TIMESTAMPTZ,
    last_health_at  TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
""")

# ============================================================================
# 11. Site A unique — Training sessions (ML learning service)
# ============================================================================
_s("""
CREATE TABLE IF NOT EXISTS training_sessions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_name      TEXT NOT NULL DEFAULT 'emotion_model',
    dataset_size    INT DEFAULT 0,
    epochs          INT DEFAULT 8,
    final_loss      DOUBLE PRECISION,
    status          TEXT DEFAULT 'pending',
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    artifact_path   TEXT,
    meta            JSONB DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
""")

# ============================================================================
# 12. Site A unique — eSIM profiles
# ============================================================================
_s("""
CREATE TABLE IF NOT EXISTS esim_profiles (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    iccid           TEXT UNIQUE NOT NULL,
    profile_name    TEXT DEFAULT 'BRIDGE-OS-GLOBAL',
    carrier         TEXT,
    status          TEXT DEFAULT 'active',
    data_remaining_gb DOUBLE PRECISION DEFAULT 0.0,
    activated_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
""")

# ============================================================================
# 13. Site A unique — TTS requests log
# ============================================================================
_s("""
CREATE TABLE IF NOT EXISTS tts_requests (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    twin_id         TEXT,
    text_length     INT NOT NULL DEFAULT 0,
    voice_id        TEXT,
    provider        TEXT DEFAULT 'elevenlabs',
    duration_ms     INT,
    status          TEXT DEFAULT 'completed',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
""")

# ============================================================================
# 14. Site A unique — DEX trade history (bridgeos dex service)
# ============================================================================
_s("""
CREATE TABLE IF NOT EXISTS dex_trades (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    address         TEXT NOT NULL,
    from_token      TEXT NOT NULL,
    to_token        TEXT NOT NULL,
    amount_in       DOUBLE PRECISION NOT NULL,
    amount_out      DOUBLE PRECISION NOT NULL,
    rate            DOUBLE PRECISION NOT NULL,
    fee             DOUBLE PRECISION DEFAULT 0.0,
    status          TEXT DEFAULT 'completed',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
""")

# ============================================================================
# 15. System configuration key-value store
# ============================================================================
_s("""
CREATE TABLE IF NOT EXISTS system_config (
    key         TEXT PRIMARY KEY,
    value       JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);
""")

# ============================================================================
# 16. Indexes
# ============================================================================
_IDX = [
    # users / auth
    ("idx_users_referral_code", "users", "referral_code"),
    ("idx_users_email", "users", "email"),
    ("idx_sessions_token", "sessions", "token"),
    ("idx_sessions_user", "sessions", "user_id"),
    ("idx_api_keys_user", "api_keys", "user_id"),
    # referrals / commissions / payments
    ("idx_referrals_referrer", "referrals", "referrer_code"),
    ("idx_commissions_user", "commissions", "user_id"),
    ("idx_payments_user", "payments", "user_id"),
    # defi
    ("idx_defi_users_google_sub", "defi_users", "google_sub"),
    ("idx_defi_users_email", "defi_users", "email"),
    ("idx_defi_refresh_tokens_user", "defi_refresh_tokens", "user_id"),
    ("idx_defi_refresh_tokens_hash", "defi_refresh_tokens", "token_hash"),
    ("idx_defi_loans_borrower", "defi_loans", "borrower_id"),
    ("idx_defi_loans_status", "defi_loans", "status"),
    ("idx_defi_loan_payments_loan", "defi_loan_payments", "loan_id"),
    ("idx_defi_stakes_user", "defi_stakes", "user_id"),
    ("idx_defi_stakes_status", "defi_stakes", "status"),
    ("idx_defi_yield_user", "defi_yield_positions", "user_id"),
    ("idx_defi_swaps_user", "defi_swaps", "user_id"),
    ("idx_defi_swaps_executed", "defi_swaps", "executed_at"),
    ("idx_defi_dex_prices_token", "defi_dex_prices", "token"),
    ("idx_defi_dex_prices_fetched", "defi_dex_prices", "fetched_at"),
    ("idx_defi_tax_lots_user", "defi_tax_lots", "user_id"),
    ("idx_defi_wallet_sessions_user", "defi_wallet_sessions", "user_id"),
    ("idx_defi_wallet_sessions_addr", "defi_wallet_sessions", "address"),
    ("idx_defi_portfolio_user", "defi_portfolio_snapshots", "user_id"),
    ("idx_defi_portfolio_snapped", "defi_portfolio_snapshots", "snapped_at"),
    # crm
    ("idx_crm_leads_email", "crm_leads", "email"),
    ("idx_crm_leads_stage", "crm_leads", "stage"),
    ("idx_crm_activities_lead", "crm_activities", "lead_id"),
    ("idx_crm_deals_lead", "crm_deals", "lead_id"),
    # invoices
    ("idx_invoices_client_email", "invoices", "client_email"),
    ("idx_invoices_status", "invoices", "status"),
    # economy
    ("idx_treasury_ledger_created", "treasury_ledger", "created_at"),
    ("idx_marketplace_tasks_status", "marketplace_tasks", "status"),
    # governance
    ("idx_gov_proposals_status", "governance_proposals", "status"),
    ("idx_gov_votes_proposal", "governance_votes", "proposal_id"),
    # twins
    ("idx_twins_twin_id", "twins", "twin_id"),
    # network
    ("idx_network_nodes_node_id", "network_nodes", "node_id"),
    # site-a unique
    ("idx_runtime_services_name", "runtime_services", "service_name"),
    ("idx_esim_profiles_user", "esim_profiles", "user_id"),
    ("idx_esim_profiles_iccid", "esim_profiles", "iccid"),
    ("idx_tts_requests_user", "tts_requests", "user_id"),
    ("idx_dex_trades_address", "dex_trades", "address"),
    ("idx_dex_trades_created", "dex_trades", "created_at"),
]

for idx_name, table, column in _IDX:
    _s(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column});")


# ============================================================================
# 17. Updated-at trigger function (reusable)
# ============================================================================
_s("""
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
""")

_UPDATED_AT_TABLES = [
    "users", "defi_users", "crm_leads", "crm_deals",
    "twins", "agent_reputation", "system_config",
]
for t in _UPDATED_AT_TABLES:
    _s(f"""
DO $$ BEGIN
    CREATE TRIGGER trg_{t}_updated_at
    BEFORE UPDATE ON {t}
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
""")


# ============================================================================
# Public API
# ============================================================================
async def run_migration(database_url: str) -> int:
    """Execute the migration against *database_url*. Returns statement count."""
    import asyncpg  # type: ignore[import-untyped]

    conn = await asyncpg.connect(database_url)
    try:
        for stmt in STATEMENTS:
            await conn.execute(stmt)
    finally:
        await conn.close()
    return len(STATEMENTS)


def run_migration_sync(database_url: str) -> int:
    """Synchronous wrapper around run_migration."""
    import asyncio
    return asyncio.run(run_migration(database_url))
