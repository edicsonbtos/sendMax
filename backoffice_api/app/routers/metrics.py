"""Router: Metricas y Dashboard (M9 hardened)

Fixes aplicados:
- FIX1: Guard admin para wallets en company-overview (operadores no ven tesoreria)
- FIX2: total_volume_usd calculado (USD/USDT pagado, era 0 hardcodeado)
- FIX3: ORIGEN_CONFIRMADO incluido en metricas y pending
- FIX4: overview total_orders usa COUNT(*)
- FIX5: awaiting_paid_proof filtra estados activos
- FIX6: company-overview elimina query redundante (paid_usd_usdt derivado en Python)
- FIX7: p2p-prices aplica LIMIT siempre + ge=1 hardening
- FIX8: pending_orders consistente entre overview y company-overview
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, HTTPException
from ..db import fetch_one, fetch_all
from ..auth import require_operator_or_admin

router = APIRouter(tags=["metrics"])

# ============================================================
# Estados de ordenes (fuente unica)
# ============================================================

ST_CREADA = "CREADA"
ST_ORIGEN = "ORIGEN_VERIFICANDO"
ST_ORIGEN_CONFIRMADO = "ORIGEN_CONFIRMADO"
ST_PROCESO = "EN_PROCESO"
ST_PAGADA = "PAGADA"
ST_CANCELADA = "CANCELADA"

PENDING_STATES = (ST_CREADA, ST_ORIGEN, ST_ORIGEN_CONFIRMADO, ST_PROCESO)


# ============================================================
# Helpers
# ============================================================

def _is_admin(auth: dict) -> bool:
    """True si el usuario es admin o usa api_key."""
    role = (auth.get("role") or "").upper()
    return role == "ADMIN" or auth.get("auth") == "api_key"


def _op_filter(auth: dict):
    """Admins ven todo. Operadores solo sus ordenes. Fail-closed si no hay user_id."""
    if _is_admin(auth):
        return "", ()
    user_id = auth.get("user_id")
    if not user_id:
        raise HTTPException(status_code=403, detail="user_id no encontrado en token")
    return " AND operator_user_id = %s", (user_id,)


# ============================================================
# GET /metrics/overview
# ============================================================

@router.get("/metrics/overview")
def metrics_overview(auth: dict = Depends(require_operator_or_admin)):
    wh, prm = _op_filter(auth)

    row = fetch_one(
        f"""
        SELECT
          COUNT(*) AS total_orders,

          COUNT(*) FILTER (WHERE status=%s) AS creadas,
          COUNT(*) FILTER (WHERE status=%s) AS origen_verificando,
          COUNT(*) FILTER (WHERE status=%s) AS origen_confirmado,
          COUNT(*) FILTER (WHERE status=%s) AS en_proceso,
          COUNT(*) FILTER (WHERE status=%s) AS pagadas,
          COUNT(*) FILTER (WHERE status=%s) AS canceladas,

          COUNT(*) FILTER (
              WHERE awaiting_paid_proof = true
                AND status NOT IN (%s, %s)
          ) AS awaiting_paid_proof,

          COALESCE(SUM(profit_usdt) FILTER (WHERE status=%s), 0) AS total_profit_usd,
          COALESCE(SUM(profit_real_usdt) FILTER (WHERE status=%s), 0) AS total_profit_real_usd,

          COALESCE(SUM(payout_dest) FILTER (
              WHERE status=%s AND dest_currency IN ('USD','USDT')
          ), 0) AS total_volume_usd
        FROM orders
        WHERE 1=1 {wh}
        """,
        (
            ST_CREADA, ST_ORIGEN, ST_ORIGEN_CONFIRMADO, ST_PROCESO, ST_PAGADA, ST_CANCELADA,
            ST_CANCELADA, ST_PAGADA,
            ST_PAGADA, ST_PAGADA,
            ST_PAGADA,
        ) + prm,
    )

    row = row or {}

    creadas = int(row.get("creadas") or 0)
    origen_verificando = int(row.get("origen_verificando") or 0)
    origen_confirmado = int(row.get("origen_confirmado") or 0)
    en_proceso = int(row.get("en_proceso") or 0)
    pagadas = int(row.get("pagadas") or 0)
    canceladas = int(row.get("canceladas") or 0)

    return {
        "total_orders": int(row.get("total_orders") or 0),
        "pending_orders": creadas + origen_verificando + origen_confirmado + en_proceso,
        "completed_orders": pagadas,
        "cancelled_orders": canceladas,
        "awaiting_paid_proof": int(row.get("awaiting_paid_proof") or 0),
        "total_volume_usd": float(row.get("total_volume_usd") or 0),
        "total_profit_usd": float(row.get("total_profit_usd") or 0),
        "total_profit_real_usd": float(row.get("total_profit_real_usd") or 0),
        "status_counts": {
            ST_CREADA: creadas,
            ST_ORIGEN: origen_verificando,
            ST_ORIGEN_CONFIRMADO: origen_confirmado,
            ST_PROCESO: en_proceso,
            ST_PAGADA: pagadas,
            ST_CANCELADA: canceladas,
        },
    }


# ============================================================
# GET /metrics/profit_daily
# ============================================================

@router.get("/metrics/profit_daily")
def profit_daily(days: int = Query(default=30, le=90), auth: dict = Depends(require_operator_or_admin)):
    from ..audit import get_profit_daily
    return {"days": days, "profit_by_day": get_profit_daily(days)}


# ============================================================
# GET /operators/ranking
# ============================================================

@router.get("/operators/ranking")
def operators_ranking(days: int = Query(default=7, le=90), auth: dict = Depends(require_operator_or_admin)):
    from ..audit import get_operators_ranking
    return {"ok": True, "days": days, "operators": get_operators_ranking(days)}


# ============================================================
# GET /metrics/corridors
# ============================================================

@router.get("/metrics/corridors")
def metrics_corridors(days: int = Query(default=30, le=90), auth: dict = Depends(require_operator_or_admin)):
    from ..audit import get_corridors
    return {"ok": True, "days": days, "corridors": get_corridors(days)}


# ============================================================
# GET /metrics/p2p-prices
# ============================================================

@router.get("/metrics/p2p-prices")
def metrics_p2p_prices(
    country: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    auth: dict = Depends(require_operator_or_admin),
):
    if country:
        rows = fetch_all(
            """
            SELECT p.country, p.fiat, p.buy_price, p.sell_price,
                   p.source, p.is_verified, p.methods_used, p.amount_ref,
                   p.rate_version_id, v.created_at
            FROM p2p_country_prices p
            JOIN rate_versions v ON v.id = p.rate_version_id
            WHERE p.country = %s
            ORDER BY v.created_at DESC
            LIMIT %s
            """,
            (country.strip().upper(), limit),
        )
    else:
        rows = fetch_all(
            """
            SELECT p.country, p.fiat, p.buy_price, p.sell_price,
                   p.source, p.is_verified, p.methods_used, p.amount_ref,
                   p.rate_version_id, v.created_at
            FROM p2p_country_prices p
            JOIN rate_versions v ON v.id = p.rate_version_id
            WHERE v.is_active = true
            ORDER BY p.country
            LIMIT %s
            """,
            (limit,),
        )

    def iso(x):
        return x.isoformat() if x else None

    items = []
    for r in rows or []:
        buy = float(r["buy_price"]) if r.get("buy_price") is not None else None
        sell = float(r["sell_price"]) if r.get("sell_price") is not None else None
        spread = None
        if buy is not None and sell is not None and sell > 0:
            spread = round(((buy - sell) / sell) * 100, 4)

        items.append({
            "country": r.get("country"),
            "fiat": r.get("fiat"),
            "buy_price": buy,
            "sell_price": sell,
            "spread_pct": spread,
            "source": r.get("source"),
            "captured_at": iso(r.get("created_at")),
            "is_verified": bool(r.get("is_verified", False)),
            "methods_used": r.get("methods_used"),
            "rate_version_id": r.get("rate_version_id"),
        })

    return {"ok": True, "count": len(items), "items": items}


# ============================================================
# GET /metrics/company-overview
# ============================================================

@router.get("/metrics/company-overview")
def metrics_company_overview(auth: dict = Depends(require_operator_or_admin)):
    wh, prm = _op_filter(auth)
    admin = _is_admin(auth)

    # --- Query 1: conteos + profit (siempre) ---
    row = fetch_one(
        f"""
        SELECT
          COUNT(*) AS total_orders,
          COUNT(*) FILTER (WHERE status IN
              ('CREADA','ORIGEN_VERIFICANDO','ORIGEN_CONFIRMADO','EN_PROCESO')
          ) AS pending_orders,
          COUNT(*) FILTER (WHERE status='PAGADA') AS completed_orders,
          COALESCE(SUM(profit_usdt) FILTER (WHERE status='PAGADA'), 0) AS total_profit_usd,
          COALESCE(SUM(profit_real_usdt) FILTER (WHERE status='PAGADA'), 0) AS total_profit_real_usd
        FROM orders
        WHERE 1=1 {wh}
        """,
        prm,
    ) or {}

    # --- Query 2: volumen por dest_currency (siempre) ---
    v_rows = fetch_all(
        f"""
        SELECT dest_currency, COALESCE(SUM(payout_dest),0) AS vol, COUNT(*) AS cnt
        FROM orders
        WHERE status='PAGADA' {wh}
        GROUP BY dest_currency
        ORDER BY vol DESC
        """,
        prm,
    ) or []

    paid_by_dest_currency = [
        {
            "dest_currency": r["dest_currency"],
            "volume": float(r["vol"] or 0),
            "count": int(r["cnt"] or 0),
        }
        for r in v_rows
        if r.get("dest_currency") is not None
    ]

    # FIX6: derivar paid_usd_usdt en Python (elimina query redundante)
    paid_usd_usdt = sum(
        float(r["vol"] or 0)
        for r in v_rows
        if r.get("dest_currency") in ("USD", "USDT")
    )

    # --- Query 3: wallets SOLO admin (no se ejecuta para operadores) ---
    origin_wallets_data = None

    if admin:
        w_rows = fetch_all(
            """
            WITH ins AS (
              SELECT origin_country, fiat_currency, COALESCE(SUM(amount_fiat),0) AS total_in
              FROM origin_receipts_daily
              GROUP BY origin_country, fiat_currency
            ),
            outs AS (
              SELECT origin_country, fiat_currency, COALESCE(SUM(amount_fiat),0) AS total_out
              FROM origin_sweeps
              GROUP BY origin_country, fiat_currency
            )
            SELECT
              COALESCE(ins.origin_country, outs.origin_country) AS origin_country,
              COALESCE(ins.fiat_currency, outs.fiat_currency) AS fiat_currency,
              COALESCE(ins.total_in, 0) - COALESCE(outs.total_out, 0) AS current_balance
            FROM ins
            FULL OUTER JOIN outs
              ON ins.origin_country=outs.origin_country AND ins.fiat_currency=outs.fiat_currency
            ORDER BY origin_country, fiat_currency
            """
        ) or []

        wallets = []
        pending_by_currency = {}
        for r in w_rows:
            bal = float(r["current_balance"] or 0)
            cur = r["fiat_currency"]
            wallets.append({
                "origin_country": r["origin_country"],
                "fiat_currency": cur,
                "current_balance": bal,
            })
            if bal > 0:
                pending_by_currency[cur] = float(pending_by_currency.get(cur, 0.0)) + bal

        top_pending = sorted(
            [x for x in wallets if x["current_balance"] > 0],
            key=lambda x: x["current_balance"],
            reverse=True,
        )[:10]

        origin_wallets_data = {
            "pending_by_currency": pending_by_currency,
            "top_pending": top_pending,
        }

    return {
        "ok": True,
        "orders": {
            "total_orders": int(row.get("total_orders") or 0),
            "pending_orders": int(row.get("pending_orders") or 0),
            "completed_orders": int(row.get("completed_orders") or 0),
        },
        "profit": {
            "total_profit_usd": float(row.get("total_profit_usd") or 0),
            "total_profit_real_usd": float(row.get("total_profit_real_usd") or 0),
        },
        "origin_wallets": origin_wallets_data,
        "volume": {
            "paid_usd_usdt": paid_usd_usdt,
            "paid_by_dest_currency": paid_by_dest_currency,
        },
    }