"""
Endpoint: Ranking de Clientes del Operador
Retorna métricas completas por beneficiario
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging

from src.db.connection import get_async_conn
from src.api.operators import get_current_operator

router = APIRouter(prefix="/api/operators/clients", tags=["client-ranking"])
logger = logging.getLogger(__name__)


class ClientRankingResponse(BaseModel):
    beneficiary_id: int
    name: str
    phone: Optional[str]
    dest_country: str
    total_orders: int
    completed_orders: int
    total_volume_usdt: float
    last_order_date: Optional[datetime]
    rank: int


@router.get("/ranking", response_model=List[ClientRankingResponse])
async def get_client_ranking(
    user_id: int = Depends(get_current_operator),
    limit: int = 50
):
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                WITH client_stats AS (
                    SELECT 
                        sb.id as beneficiary_id,
                        COALESCE(sb.full_name, sb.alias) as name,
                        sb.phone,
                        sb.dest_country,
                        COUNT(o.id) as total_orders,
                        COUNT(CASE WHEN o.status IN ('COMPLETADA', 'ORIGEN_CONFIRMADO') THEN 1 END) as completed_orders,
                        COALESCE(SUM(CASE WHEN o.status IN ('COMPLETADA', 'ORIGEN_CONFIRMADO') THEN o.profit_usdt ELSE 0 END), 0) as total_volume,
                        MAX(o.created_at) as last_order_date
                    FROM saved_beneficiaries sb
                    LEFT JOIN orders o ON o.beneficiary_id = sb.id
                    WHERE sb.user_id = %s AND sb.is_active = true
                    GROUP BY sb.id, sb.full_name, sb.alias, sb.phone, sb.dest_country
                ),
                ranked AS (
                    SELECT 
                        *,
                        ROW_NUMBER() OVER (ORDER BY total_volume DESC, completed_orders DESC) as rank
                    FROM client_stats
                    WHERE total_orders > 0
                )
                SELECT * FROM ranked ORDER BY rank LIMIT %s
                """,
                (user_id, limit)
            )
            
            rows = await cur.fetchall()
            
            return [
                ClientRankingResponse(
                    beneficiary_id=r[0],
                    name=r[1] or "Sin nombre",
                    phone=r[2],
                    dest_country=r[3],
                    total_orders=r[4],
                    completed_orders=r[5],
                    total_volume_usdt=float(r[6] or 0),
                    last_order_date=r[7],
                    rank=r[8]
                )
                for r in rows
            ]


@router.get("/stats")
async def get_client_stats_summary(user_id: int = Depends(get_current_operator)):
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT 
                    COUNT(DISTINCT sb.id) as total_clients,
                    COUNT(DISTINCT CASE WHEN o.id IS NOT NULL THEN sb.id END) as active_clients,
                    COALESCE(SUM(CASE WHEN o.status IN ('COMPLETADA', 'ORIGEN_CONFIRMADO') THEN o.profit_usdt ELSE 0 END), 0) as total_volume
                FROM saved_beneficiaries sb
                LEFT JOIN orders o ON o.beneficiary_id = sb.id
                WHERE sb.user_id = %s AND sb.is_active = true
                """,
                (user_id,)
            )
            
            row = await cur.fetchone()
            
            return {
                "total_clients": row[0] or 0,
                "active_clients": row[1] or 0,
                "total_volume_usdt": float(row[2] or 0)
            }
