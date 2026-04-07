#!/usr/bin/env python3
"""
init_unified_db.py — Initialize the unified PostgreSQL database.

1. Connects via DATABASE_URL env var
2. Runs the 001_unified_schema migration
3. Seeds required system config rows
4. Verifies all expected tables exist
5. Prints a summary
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Ensure the backend root is on sys.path so we can import migrations
_backend_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_backend_root))


DATABASE_URL: str = os.environ.get("DATABASE_URL", "")

EXPECTED_TABLES: list[str] = [
    # Site A core
    "users", "referrals", "commissions", "payments", "api_keys",
    "sessions", "modules",
    # DeFi
    "defi_users", "defi_refresh_tokens", "defi_loans", "defi_loan_payments",
    "defi_stakes", "defi_yield_positions", "defi_swaps", "defi_dex_prices",
    "defi_tax_lots", "defi_subscriptions", "defi_wallet_sessions",
    "defi_portfolio_snapshots",
    # CRM
    "crm_leads", "crm_activities", "crm_deals",
    # Billing
    "invoices",
    # Economy
    "treasury_ledger", "marketplace_tasks",
    # Governance
    "governance_proposals", "governance_votes", "agent_reputation",
    # Twins / Network
    "twins", "network_nodes", "network_projects",
    # Site A unique
    "runtime_services", "training_sessions", "esim_profiles",
    "tts_requests", "dex_trades",
    # System
    "system_config",
]


async def main() -> None:
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL environment variable is not set.")
        print("  Example: postgresql://user:pass@localhost:5432/bridge_unified")
        sys.exit(1)

    # Strip async driver prefix if present — asyncpg wants plain postgresql://
    db_url = DATABASE_URL
    for prefix in ("postgresql+asyncpg://", "postgres://"):
        if db_url.startswith(prefix):
            db_url = "postgresql://" + db_url[len(prefix):]
            break

    try:
        import asyncpg  # type: ignore[import-untyped]
    except ImportError:
        print("ERROR: asyncpg is not installed. Run: pip install asyncpg")
        sys.exit(1)

    print(f"Connecting to: {_mask_url(db_url)}")

    # ── Step 1: Run migration ─────────────────────────────────────────────
    import importlib.util, pathlib
    _spec = importlib.util.spec_from_file_location(
        "unified_schema",
        pathlib.Path(__file__).parent.parent / "migrations" / "001_unified_schema.py",
    )
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    run_migration = _mod.run_migration

    stmt_count = await run_migration(db_url)
    print(f"Migration executed: {stmt_count} statements")

    # ── Step 2: Seed system config ────────────────────────────────────────
    conn = await asyncpg.connect(db_url)
    try:
        seeds = [
            ("schema_version", '{"version": "001_unified_schema", "applied_at": "now()"}'),
            ("system_name", '{"value": "BridgeAI Unified"}'),
        ]
        for key, value in seeds:
            await conn.execute(
                """
                INSERT INTO system_config (key, value, updated_at)
                VALUES ($1, $2::jsonb, NOW())
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
                """,
                key, value,
            )
        print(f"Seeded {len(seeds)} system_config entries")

        # ── Step 3: Verify tables ─────────────────────────────────────────
        rows = await conn.fetch(
            """
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
            """
        )
        existing = {r["tablename"] for r in rows}

        missing = [t for t in EXPECTED_TABLES if t not in existing]
        found = [t for t in EXPECTED_TABLES if t in existing]

        print()
        print("=== TABLE VERIFICATION ===")
        print(f"  Expected: {len(EXPECTED_TABLES)}")
        print(f"  Found:    {len(found)}")
        if missing:
            print(f"  MISSING:  {', '.join(missing)}")
        else:
            print("  Status:   ALL TABLES PRESENT")

        # Extra tables not in our list
        extras = existing - set(EXPECTED_TABLES)
        if extras:
            print(f"  Extra:    {', '.join(sorted(extras))}")

        print()
        print("=== SUMMARY ===")
        if missing:
            print(f"WARNING: {len(missing)} table(s) missing!")
            sys.exit(1)
        else:
            print("Database initialization complete. All tables verified.")

    finally:
        await conn.close()


def _mask_url(url: str) -> str:
    """Mask password in the URL for safe logging."""
    if "@" in url and ":" in url:
        try:
            before_at = url.split("@")[0]
            after_at = url.split("@")[1]
            proto_user = before_at.rsplit(":", 1)[0]
            return f"{proto_user}:****@{after_at}"
        except Exception:
            pass
    return url


if __name__ == "__main__":
    asyncio.run(main())
