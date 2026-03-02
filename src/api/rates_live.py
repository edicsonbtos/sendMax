from fastapi import APIRouter
import logging

from src.db.repositories.rates_repo import get_latest_active_rate_version

router = APIRouter(prefix="/api/rates", tags=["rates"])
logger = logging.getLogger(__name__)

@router.get("/current")
async def get_current_rates():
    rv = await get_latest_active_rate_version()
    if not rv:
        return {"rates": []}
    
    from src.db.connection import get_async_conn
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT origin_country, dest_country, rate_client, commission_pct
                FROM route_rates WHERE rate_version_id = %s
            """, (rv.id,))
            rows = await cur.fetchall()
            
    return {
        "timestamp": rv.created_at.isoformat(),
        "version_id": rv.id,
        "rates": [
            {
                "origin": r[0],
                "dest": r[1],
                "rate": float(r[2]),
                "commission_pct": float(r[3] * 100)
            }
            for r in rows
        ]
    }
