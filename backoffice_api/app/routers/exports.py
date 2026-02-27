"""Router: Exportación CSV — Fase 2

StreamingResponse para no cargar todo en memoria.
Endpoints:
  GET /origin-wallets/export   → CSV cierres de billetera
  GET /metrics/export-orders   → CSV órdenes con utilidad neta
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import date as _date, timedelta

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from ..auth import require_admin
from ..db import fetch_all

router = APIRouter(tags=["exports"])
logger = logging.getLogger(__name__)


def _stream_csv(rows: list[dict], columns: list[str], filename: str):
    """Genera un StreamingResponse CSV a partir de una lista de dicts."""
    def generate():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(columns)
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate(0)

        for row in rows:
            writer.writerow([row.get(c, "") for c in columns])
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate(0)

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ============================================================
# GET /origin-wallets/export
# ============================================================

@router.get("/origin-wallets/export")
def export_wallet_closures(
    date_from: str | None = Query(None, description="YYYY-MM-DD"),
    date_to: str | None = Query(None, description="YYYY-MM-DD"),
    origin_country: str | None = Query(None),
    auth: dict = Depends(require_admin),
):
    """Exporta cierres de billeteras de origen como CSV."""
    conditions = []
    params: list = []

    if date_from:
        conditions.append("c.day >= %s")
        params.append(date_from)
    if date_to:
        conditions.append("c.day <= %s")
        params.append(date_to)
    if origin_country:
        conditions.append("c.origin_country = %s")
        params.append(origin_country.upper())

    where = (" AND " + " AND ".join(conditions)) if conditions else ""

    rows = fetch_all(
        f"""
        SELECT
            c.day,
            c.origin_country,
            c.fiat_currency,
            c.net_amount_at_close,
            c.closed_at,
            c.closed_by_telegram_id,
            c.note,
            COALESCE(
                (SELECT SUM(r.amount_fiat) FROM origin_receipts_daily r
                 WHERE r.day = c.day AND r.origin_country = c.origin_country
                   AND r.fiat_currency = c.fiat_currency), 0
            ) AS total_ingresos,
            COALESCE(
                (SELECT SUM(s.amount_fiat) FROM origin_sweeps s
                 WHERE s.day = c.day AND s.origin_country = c.origin_country
                   AND s.fiat_currency = c.fiat_currency), 0
            ) AS total_egresos
        FROM origin_wallet_closures c
        WHERE 1=1 {where}
        ORDER BY c.day DESC, c.origin_country
        LIMIT 10000
        """,
        tuple(params),
    )

    columns = [
        "day", "origin_country", "fiat_currency",
        "total_ingresos", "total_egresos", "net_amount_at_close",
        "closed_at", "closed_by_telegram_id", "note",
    ]

    # Serialize datetimes
    for r in rows:
        if r.get("closed_at"):
            r["closed_at"] = str(r["closed_at"])
        for k in ("total_ingresos", "total_egresos", "net_amount_at_close"):
            if r.get(k) is not None:
                r[k] = float(r[k])

    d_from = date_from or "all"
    d_to = date_to or "today"
    return _stream_csv(rows, columns, f"cierres_billetera_{d_from}_{d_to}.csv")


# ============================================================
# GET /metrics/export-orders
# ============================================================

@router.get("/metrics/export-orders")
def export_orders(
    date_from: str | None = Query(None, description="YYYY-MM-DD"),
    date_to: str | None = Query(None, description="YYYY-MM-DD"),
    origin_country: str | None = Query(None),
    status: str | None = Query(None),
    auth: dict = Depends(require_admin),
):
    """Exporta órdenes con utilidad neta como CSV."""
    conditions = []
    params: list = []

    if date_from:
        conditions.append("o.created_at >= %s::timestamptz")
        params.append(date_from)
    if date_to:
        conditions.append("o.created_at < (%s::date + interval '1 day')::timestamptz")
        params.append(date_to)
    if origin_country:
        conditions.append("o.origin_country = %s")
        params.append(origin_country.upper())
    if status:
        conditions.append("o.status = %s")
        params.append(status.upper())

    where = (" AND " + " AND ".join(conditions)) if conditions else ""

    rows = fetch_all(
        f"""
        SELECT
            o.public_id,
            o.created_at,
            o.status,
            o.origin_country,
            o.dest_country,
            o.amount_origin,
            o.payout_dest,
            o.rate_client,
            o.commission_pct,
            o.profit_usdt AS utilidad_teorica,
            o.profit_real_usdt AS utilidad_neta_real,
            o.execution_price_buy,
            o.execution_price_sell,
            o.paid_at,
            o.cancel_reason,
            u.alias AS operador
        FROM orders o
        LEFT JOIN users u ON u.id = o.operator_user_id
        WHERE 1=1 {where}
        ORDER BY o.created_at DESC
        LIMIT 50000
        """,
        tuple(params),
    )

    columns = [
        "public_id", "created_at", "status",
        "origin_country", "dest_country",
        "amount_origin", "payout_dest",
        "rate_client", "commission_pct",
        "utilidad_teorica", "utilidad_neta_real",
        "execution_price_buy", "execution_price_sell",
        "paid_at", "cancel_reason", "operador",
    ]

    for r in rows:
        for k in ("created_at", "paid_at"):
            if r.get(k):
                r[k] = str(r[k])
        for k in ("amount_origin", "payout_dest", "rate_client", "commission_pct",
                   "utilidad_teorica", "utilidad_neta_real",
                   "execution_price_buy", "execution_price_sell"):
            if r.get(k) is not None:
                r[k] = float(r[k])

    d_from = date_from or "all"
    d_to = date_to or "today"
    return _stream_csv(rows, columns, f"ordenes_utilidad_{d_from}_{d_to}.csv")
