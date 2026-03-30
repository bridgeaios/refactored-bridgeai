from fastapi import APIRouter, HTTPException
from db import db

router = APIRouter()


@router.get("/api/ledger/")
async def get_ledger(account: str = None, limit: int = 100):
    """Get ledger entries"""
    try:
        if account:
            entries = await db.fetch("""
                SELECT * FROM ledger WHERE account=$1
                ORDER BY timestamp DESC LIMIT $2
            """, account, limit)
        else:
            entries = await db.fetch("""
                SELECT * FROM ledger
                ORDER BY timestamp DESC LIMIT $1
            """, limit)

        return [dict(e) for e in entries]
    except Exception as e:
        import logging as _log; _log.getLogger(__name__).exception("internal error"); raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/api/ledger/account/{account_id}")
async def get_account_balance(account_id: str):
    """Get account total balance"""
    try:
        total = await db.fetchval("""
            SELECT COALESCE(SUM(amount), 0) FROM ledger WHERE account=$1
        """, account_id)

        return {
            "account": account_id,
            "balance": float(total) if total else 0.0
        }
    except Exception as e:
        import logging as _log; _log.getLogger(__name__).exception("internal error"); raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/api/ledger/summary")
async def get_ledger_summary():
    """Get ledger summary by transaction type"""
    try:
        summary = await db.fetch("""
            SELECT transaction_type, COUNT(*) as count, SUM(amount) as total
            FROM ledger
            GROUP BY transaction_type
            ORDER BY total DESC
        """)

        return [dict(s) for s in summary]
    except Exception as e:
        import logging as _log; _log.getLogger(__name__).exception("internal error"); raise HTTPException(status_code=500, detail="Internal server error")
