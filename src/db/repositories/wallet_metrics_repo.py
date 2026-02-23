from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.db.connection import get_async_conn


@dataclass(frozen=True)
class WalletMetrics:
    profit_today_usdt: Decimal
    profit_month_usdt: Decimal
    referrals_month_usdt: Decimal


async def get_wallet_metrics(user_id: int) -> WalletMetrics:
    """
    Métricas basadas en ledger (append-only):
    - profit_today_usdt: suma de ORDER_PROFIT del día (UTC)
    - profit_month_usdt: suma de ORDER_PROFIT del mes (UTC)
    - referrals_month_usdt: suma de SPONSOR_COMMISSION del mes (UTC)
    """
    sql = """
    WITH
      today AS (
        SELECT COALESCE(SUM(amount_usdt), 0) AS v
        FROM wallet_ledger
        WHERE user_id = %s
          AND type = 'ORDER_PROFIT'
          AND created_at >= date_trunc('day', now())
      ),
      month_profit AS (
        SELECT COALESCE(SUM(amount_usdt), 0) AS v
        FROM wallet_ledger
        WHERE user_id = %s
          AND type = 'ORDER_PROFIT'
          AND created_at >= date_trunc('month', now())
      ),
      month_ref AS (
        SELECT COALESCE(SUM(amount_usdt), 0) AS v
        FROM wallet_ledger
        WHERE user_id = %s
          AND type = 'SPONSOR_COMMISSION'
          AND created_at >= date_trunc('month', now())
      )
    SELECT (SELECT v FROM today),
           (SELECT v FROM month_profit),
           (SELECT v FROM month_ref);
    """
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (user_id, user_id, user_id))
            rows = await cur.fetchall()
            row = rows[0]
            return WalletMetrics(
                profit_today_usdt=Decimal(str(row[0])),
                profit_month_usdt=Decimal(str(row[1])),
                referrals_month_usdt=Decimal(str(row[2])),
            )
