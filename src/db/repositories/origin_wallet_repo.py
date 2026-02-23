from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from psycopg.rows import dict_row

from src.db.connection import get_async_conn

logger = logging.getLogger(__name__)


@dataclass
class OriginReceiptDaily:
    day: date
    origin_country: str
    fiat_currency: str
    amount_fiat: Decimal
    approved_by_telegram_id: int | None
    approved_note: str | None
    ref_order_public_id: int | None


async def add_origin_receipt_ledger_tx(
    conn: psycopg.AsyncConnection,
    *,
    ref_order_public_id: int,
    day: date,
    origin_country: str,
    fiat_currency: str,
    amount_fiat: Decimal,
    approved_by_telegram_id: int | None = None,
    approved_note: str | None = None,
) -> bool:
    """
    Registra un ingreso en el ledger por orden. Idempotente por ref_order_public_id.
    """
    sql = """
        INSERT INTO origin_receipts_ledger
          (ref_order_public_id, day, origin_country, fiat_currency, amount_fiat,
           approved_by_telegram_id, approved_note, approved_at)
        VALUES
          (%s, %s, %s, %s, %s,
           %s, %s, now())
        ON CONFLICT (ref_order_public_id) DO NOTHING
        RETURNING id;
    """
    async with conn.cursor() as cur:
        await cur.execute(
            sql,
            (
                ref_order_public_id,
                day,
                origin_country,
                fiat_currency,
                amount_fiat,
                approved_by_telegram_id,
                approved_note,
            ),
        )
        row = await cur.fetchone()
        return bool(row)


async def add_origin_receipt_daily_tx(
    conn: psycopg.AsyncConnection,
    *,
    day: date,
    origin_country: str,
    fiat_currency: str,
    amount_fiat: Decimal,
    approved_by_telegram_id: int | None = None,
    approved_note: str | None = None,
    ref_order_public_id: int | None = None,
) -> int:
    """
    Versión transaccional de add_origin_receipt_daily.
    """
    sql = """
        INSERT INTO origin_receipts_daily
          (day, origin_country, fiat_currency, amount_fiat,
           approved_at, approved_by_telegram_id, approved_note,
           ref_order_public_id)
        VALUES
          (%s, %s, %s, %s,
           now(), %s, %s,
           %s)
        ON CONFLICT (day, origin_country, fiat_currency) DO UPDATE SET
          amount_fiat = origin_receipts_daily.amount_fiat + EXCLUDED.amount_fiat,
          approved_at = EXCLUDED.approved_at,
          approved_by_telegram_id = EXCLUDED.approved_by_telegram_id,
          approved_note = EXCLUDED.approved_note,
          ref_order_public_id = EXCLUDED.ref_order_public_id
        RETURNING id;
    """
    async with conn.cursor() as cur:
        await cur.execute(
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
        row = await cur.fetchone()
        return int(row[0]) if row else 0


async def add_origin_receipt_daily(
    *,
    day: date,
    origin_country: str,
    fiat_currency: str,
    amount_fiat: Decimal,
    approved_by_telegram_id: int | None = None,
    approved_note: str | None = None,
    ref_order_public_id: int | None = None,
) -> int:
    """
    Registra ingreso de origen. Si ya existe registro para ese dia/pais/moneda, acumula el monto.
    """
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            res = await add_origin_receipt_daily_tx(
                conn,
                day=day,
                origin_country=origin_country,
                fiat_currency=fiat_currency,
                amount_fiat=amount_fiat,
                approved_by_telegram_id=approved_by_telegram_id,
                approved_note=approved_note,
                ref_order_public_id=ref_order_public_id,
            )
            await conn.commit()
            return res
