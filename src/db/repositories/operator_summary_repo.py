from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
import psycopg

from src.config.settings import settings


@dataclass(frozen=True)
class OrderSummaryRow:
    public_id: int
    origin_country: str
    dest_country: str
    amount_origin: Decimal
    payout_dest: Decimal
    status: str
    created_at: datetime
    origin_payment_proof_file_id: str
    dest_payment_proof_file_id: str | None


def get_conn():
    return psycopg.connect(settings.DATABASE_URL)


def list_recent_orders_for_operator(operator_user_id: int, limit: int = 10) -> list[OrderSummaryRow]:
    sql = """
        SELECT
            public_id,
            origin_country,
            dest_country,
            amount_origin,
            payout_dest,
            status,
            created_at,
            origin_payment_proof_file_id,
            dest_payment_proof_file_id
        FROM orders
        WHERE operator_user_id = %s
        ORDER BY created_at DESC
        LIMIT %s;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (operator_user_id, limit))
            rows = cur.fetchall()
            return [OrderSummaryRow(*r) for r in rows]
