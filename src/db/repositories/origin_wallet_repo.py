from __future__ import annotations

import logging
logger = logging.getLogger(__name__)

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row



from src.db.connection import get_conn


@dataclass
class OriginReceiptDaily:
    day: date
    origin_country: str
    fiat_currency: str
    amount_fiat: Decimal
    approved_by_telegram_id: int | None
    approved_note: str | None
    ref_order_public_id: int | None


def add_origin_receipt_daily(
    *,
    day: date,
    origin_country: str,
    fiat_currency: str,
    amount_fiat: Decimal,
    approved_by_telegram_id: int | None = None,
    approved_note: str | None = None,
    ref_order_public_id: int | None = None,
) -> int:
    sql = """
        INSERT INTO origin_receipts_daily
          (day, origin_country, fiat_currency, amount_fiat,
           approved_at, approved_by_telegram_id, approved_note,
           ref_order_public_id)
        VALUES
          (%s, %s, %s, %s,
           now(), %s, %s,
           %s)
        RETURNING id;
    """
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                sql,
                (
                    day,
                    origin_country,
                    fiat_currency,
                    amount_fiat,
                    approved_by_telegram_id,
                    approved_note,
                    ref_order_public_id,
                ),
            )
            row = cur.fetchone()
            conn.commit()
            return int(row["id"])
