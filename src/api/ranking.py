from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from decimal import Decimal

from src.db.connection import get_async_conn

router = APIRouter(prefix="/api/ranking", tags=["ranking"])

class RankingEntry(BaseModel):
    position: int
    user_id: int
    alias: str
    trust_score: Decimal
    total_orders: int
    monthly_volume_usdt: Decimal

@router.get("/operators", response_model=List[RankingEntry])
async def get_operator_ranking(limit: int = 10):
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                WITH monthly_stats AS (
                    SELECT operator_id, COUNT(*) as orders_count,
                    COALESCE(SUM(profit_real_usdt), 0) as volume
                    FROM orders
                    WHERE DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE)
                    AND status IN ('COMPLETADA', 'ORIGEN_CONFIRMADO')
                    GROUP BY operator_id
                ),
                ranked AS (
                    SELECT u.id, u.alias, u.trust_score,
                    COALESCE(ms.orders_count, 0) as total_orders,
                    COALESCE(ms.volume, 0) as monthly_volume,
                    ROW_NUMBER() OVER (ORDER BY u.trust_score DESC, ms.volume DESC) as position
                    FROM users u
                    LEFT JOIN monthly_stats ms ON u.id = ms.operator_id
                    WHERE u.kyc_status = 'APPROVED'
                )
                SELECT * FROM ranked ORDER BY position LIMIT %s
            """, (limit,))
            rows = await cur.fetchall()
            return [RankingEntry(
                position=r[5], user_id=r[0], alias=r[1],
                trust_score=r[2], total_orders=r[3], monthly_volume_usdt=r[4]
            ) for r in rows]
