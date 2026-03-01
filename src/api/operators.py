from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
import logging

from src.db.connection import get_async_conn

router = APIRouter(prefix="/api/operators", tags=["operators"])
logger = logging.getLogger(__name__)

class OperatorStatsResponse(BaseModel):
    daily_volume_usdt: Decimal
    monthly_volume_usdt: Decimal
    total_orders: int
    pending_orders: int
    trust_score: Decimal
    rank_position: Optional[int]

class TopClientResponse(BaseModel):
    name: str
    total_volume_usdt: Decimal
    total_orders: int

class OrderQueueItem(BaseModel):
    public_id: int
    client_name: str
    amount_origin: Decimal
    origin_country: str
    dest_country: str
    status: str
    created_at: datetime

class EarningsByCountry(BaseModel):
    country: str
    earnings_usdt: Decimal
    order_count: int

async def get_current_operator(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="No autorizado")
    try:
        user_id = int(authorization.replace("Bearer ", ""))
        return user_id
    except:
        raise HTTPException(status_code=401, detail="Token inválido")

@router.get("/dashboard/stats", response_model=OperatorStatsResponse)
async def get_dashboard_stats(user_id: int = Depends(get_current_operator)):
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT COALESCE(SUM(profit_real_usdt), 0)
                FROM orders
                WHERE operator_id = %s AND DATE(created_at) = CURRENT_DATE
                AND status IN ('COMPLETADA', 'ORIGEN_CONFIRMADO')
            """, (user_id,))
            daily_vol = (await cur.fetchone())[0]
            
            await cur.execute("""
                SELECT COALESCE(SUM(profit_real_usdt), 0)
                FROM orders
                WHERE operator_id = %s
                AND DATE_TRUNC('month', created_at) = DATE_TRUNC('month', CURRENT_DATE)
                AND status IN ('COMPLETADA', 'ORIGEN_CONFIRMADO')
            """, (user_id,))
            monthly_vol = (await cur.fetchone())[0]
            
            await cur.execute("SELECT COUNT(*) FROM orders WHERE operator_id = %s", (user_id,))
            total_orders = (await cur.fetchone())[0]
            
            await cur.execute("""
                SELECT COUNT(*) FROM orders WHERE operator_id = %s
                AND status IN ('CREADA', 'ORIGEN_VERIFICANDO', 'ORIGEN_CONFIRMADO')
            """, (user_id,))
            pending = (await cur.fetchone())[0]
            
            await cur.execute("SELECT trust_score FROM users WHERE id = %s", (user_id,))
            trust = (await cur.fetchone())[0] or Decimal("50")
            
            await cur.execute("""
                WITH ranked AS (
                    SELECT id, ROW_NUMBER() OVER (ORDER BY trust_score DESC) as rank
                    FROM users WHERE kyc_status = 'APPROVED'
                )
                SELECT rank FROM ranked WHERE id = %s
            """, (user_id,))
            rank_row = await cur.fetchone()
            rank = rank_row[0] if rank_row else None
            
            return OperatorStatsResponse(
                daily_volume_usdt=daily_vol,
                monthly_volume_usdt=monthly_vol,
                total_orders=total_orders,
                pending_orders=pending,
                trust_score=trust,
                rank_position=rank
            )

@router.get("/dashboard/top-clients", response_model=List[TopClientResponse])
async def get_top_clients(user_id: int = Depends(get_current_operator), limit: int = 5):
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT 
                    COALESCE(o.beneficiary_text, 'Cliente Manual') as name,
                    SUM(o.profit_real_usdt) as total_volume,
                    COUNT(*) as total_orders
                FROM orders o
                WHERE o.operator_id = %s AND o.status IN ('COMPLETADA', 'ORIGEN_CONFIRMADO')
                GROUP BY o.beneficiary_id, o.beneficiary_text
                ORDER BY total_volume DESC LIMIT %s
            """, (user_id, limit))
            rows = await cur.fetchall()
            return [TopClientResponse(name=r[0][:50], total_volume_usdt=r[1], total_orders=r[2]) for r in rows]

@router.get("/orders/queue", response_model=List[OrderQueueItem])
async def get_order_queue(user_id: int = Depends(get_current_operator)):
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT public_id, COALESCE(beneficiary_text, 'Sin nombre') as client_name,
                amount_origin, origin_country, dest_country, status, created_at
                FROM orders WHERE operator_id = %s
                AND status IN ('CREADA', 'ORIGEN_VERIFICANDO', 'ORIGEN_CONFIRMADO', 'PAGO_PENDIENTE')
                ORDER BY created_at DESC LIMIT 20
            """, (user_id,))
            rows = await cur.fetchall()
            return [OrderQueueItem(
                public_id=r[0], client_name=r[1][:30], amount_origin=r[2],
                origin_country=r[3], dest_country=r[4], status=r[5], created_at=r[6]
            ) for r in rows]

@router.get("/earnings/by-country", response_model=List[EarningsByCountry])
async def get_earnings_by_country(user_id: int = Depends(get_current_operator), days: int = 30):
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT dest_country, SUM(profit_real_usdt) as earnings, COUNT(*) as order_count
                FROM orders WHERE operator_id = %s
                AND created_at >= CURRENT_DATE - INTERVAL '%s days'
                AND status IN ('COMPLETADA', 'ORIGEN_CONFIRMADO')
                GROUP BY dest_country ORDER BY earnings DESC
            """, (user_id, days))
            rows = await cur.fetchall()
            return [EarningsByCountry(country=r[0], earnings_usdt=r[1], order_count=r[2]) for r in rows]

class OrderListItem(BaseModel):
    public_id: int
    origin_country: str
    dest_country: str
    amount_origin: Decimal
    payout_dest: Decimal
    status: str
    created_at: datetime
    beneficiary_text: str

@router.get("/orders", response_model=list[OrderListItem])
async def list_my_orders(
    limit: int = 50,
    status: Optional[str] = None,
    q: Optional[str] = None,
    user_id: int = Depends(get_current_operator),
):
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            where = ["operator_user_id = %s"]
            params = [user_id]

            if status and status.upper() != "TODOS":
                where.append("status = %s")
                params.append(status)

            if q and q.strip():
                qq = f"%{q.strip()}%"
                where.append("(CAST(public_id AS TEXT) ILIKE %s OR COALESCE(beneficiary_text,'') ILIKE %s)")
                params.extend([qq, qq])

            where_sql = " AND ".join(where)
            params.append(limit)

            await cur.execute(
                f"""
                SELECT public_id, origin_country, dest_country, amount_origin, payout_dest,
                       status, created_at, COALESCE(beneficiary_text,'')
                FROM orders
                WHERE {where_sql}
                ORDER BY created_at DESC
                LIMIT %s
                """,
                tuple(params),
            )
            rows = await cur.fetchall()

    return [
        OrderListItem(
            public_id=r[0],
            origin_country=r[1],
            dest_country=r[2],
            amount_origin=r[3],
            payout_dest=r[4],
            status=r[5],
            created_at=r[6],
            beneficiary_text=r[7],
        )
        for r in rows
    ]

class WalletSummaryResponse(BaseModel):
    balance_usdt: Decimal
    lifetime_earnings_usdt: Decimal
    pending_withdrawals_usdt: Decimal

@router.get("/wallet/summary", response_model=WalletSummaryResponse)
async def get_wallet_summary(user_id: int = Depends(get_current_operator)):
    summary = WalletSummaryResponse(balance_usdt=Decimal("0"), lifetime_earnings_usdt=Decimal("0"), pending_withdrawals_usdt=Decimal("0"))
    try:
        async with get_async_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT 
                        COALESCE(SUM(amount_usdt), 0) as balance 
                    FROM wallet_ledger 
                    WHERE operator_id = %s
                """, (user_id,))
                res_balance = await cur.fetchone()
                if res_balance:
                    summary.balance_usdt = res_balance[0]

                await cur.execute("""
                    SELECT 
                        COALESCE(SUM(amount_usdt), 0) as lifetime 
                    FROM wallet_ledger 
                    WHERE operator_id = %s AND amount_usdt > 0 AND type = 'EARNING'
                """, (user_id,))
                res_life = await cur.fetchone()
                if res_life:
                    summary.lifetime_earnings_usdt = res_life[0]

                await cur.execute("""
                    SELECT 
                        COALESCE(SUM(ABS(amount_usdt)), 0) as pending 
                    FROM wallet_ledger 
                    WHERE operator_id = %s AND type = 'WITHDRAWAL_PENDING'
                """, (user_id,))
                res_pend = await cur.fetchone()
                if res_pend:
                    summary.pending_withdrawals_usdt = res_pend[0]
    except Exception as e:
        logger.warning(f"Wallet ledger table info failed (might not exist): {e}")

    return summary

class LedgerItem(BaseModel):
    id: int
    amount_usdt: Decimal
    type: str
    description: str
    created_at: datetime

@router.get("/wallet/ledger", response_model=List[LedgerItem])
async def get_wallet_ledger(limit: int = 50, user_id: int = Depends(get_current_operator)):
    items = []
    try:
        async with get_async_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT id, amount_usdt, type, description, created_at 
                    FROM wallet_ledger 
                    WHERE operator_id = %s 
                    ORDER BY created_at DESC LIMIT %s
                """, (user_id, limit))
                rows = await cur.fetchall()
                for r in rows:
                    items.append(LedgerItem(
                        id=r[0],
                        amount_usdt=r[1],
                        type=r[2],
                        description=r[3],
                        created_at=r[4]
                    ))
    except Exception as e:
        logger.warning(f"Wallet ledger table read failed: {e}")
    return items

@router.post("/wallet/withdraw")
async def request_withdrawal(user_id: int = Depends(get_current_operator)):
    raise HTTPException(status_code=501, detail="Not implemented")
