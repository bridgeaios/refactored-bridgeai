from fastapi import APIRouter, HTTPException
from db import db

router = APIRouter()


@router.get("/api/treasury/")
async def get_treasury():
    """Get total treasury (sum of all positive transactions)"""
    try:
        total = await db.fetchval("""
            SELECT COALESCE(SUM(amount), 0) FROM ledger
        """)

        count = await db.fetchval("""
            SELECT COUNT(*) FROM ledger
        """)

        return {
            "treasury": {
                "total": float(total) if total else 0.0,
                "currency": "USD",
                "transactions": count or 0
            }
        }
    except Exception as e:
        import logging as _log; _log.getLogger(__name__).exception("internal error"); raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/api/treasury/breakdown")
async def get_treasury_breakdown():
    """Get treasury breakdown by transaction type"""
    try:
        breakdown = await db.fetch("""
            SELECT transaction_type, COALESCE(SUM(amount), 0) as total
            FROM ledger
            GROUP BY transaction_type
            ORDER BY total DESC
        """)

        result = {}
        total = 0
        for row in breakdown:
            trans_type = row["transaction_type"]
            amount = float(row["total"]) if row["total"] else 0.0
            result[trans_type] = amount
            total += amount

        result["total"] = total

        return result
    except Exception as e:
        import logging as _log; _log.getLogger(__name__).exception("internal error"); raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/api/treasury/stats")
async def get_treasury_stats():
    """Get advanced treasury statistics"""
    try:
        total = await db.fetchval("SELECT COALESCE(SUM(amount), 0) FROM ledger")
        count = await db.fetchval("SELECT COUNT(*) FROM ledger")
        avg = await db.fetchval("SELECT COALESCE(AVG(amount), 0) FROM ledger")

        return {
            "total": float(total) if total else 0.0,
            "count": count or 0,
            "average": float(avg) if avg else 0.0,
            "currency": "USD"
        }
    except Exception as e:
        import logging as _log; _log.getLogger(__name__).exception("internal error"); raise HTTPException(status_code=500, detail="Internal server error")
