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

import io
import csv
from datetime import date as _date
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
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
async def metrics_overview(auth: dict = Depends(require_operator_or_admin)):
    wh, prm = _op_filter(auth)

    row = await fetch_one(
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
async def profit_daily(days: int = Query(default=30, le=90), auth: dict = Depends(require_operator_or_admin)):
    from ..audit import get_profit_daily
    return {"days": days, "profit_by_day": await get_profit_daily(days)}


# ============================================================
# GET /operators/ranking
# ============================================================

@router.get("/operators/ranking")
async def operators_ranking(days: int = Query(default=7, le=90), auth: dict = Depends(require_operator_or_admin)):
    from ..audit import get_operators_ranking
    return {"ok": True, "days": days, "operators": await get_operators_ranking(days)}


# ============================================================
# GET /metrics/corridors
# ============================================================

@router.get("/metrics/corridors")
async def metrics_corridors(days: int = Query(default=30, le=90), auth: dict = Depends(require_operator_or_admin)):
    from ..audit import get_corridors
    return {"ok": True, "days": days, "corridors": await get_corridors(days)}


# ============================================================
# GET /metrics/p2p-prices
# ============================================================

@router.get("/metrics/p2p-prices")
async def metrics_p2p_prices(
    country: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    auth: dict = Depends(require_operator_or_admin),
):
    if country:
        rows = await fetch_all(
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
        rows = await fetch_all(
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
# GET /metrics/operator-leaderboard
# ============================================================

@router.get("/metrics/operator-leaderboard")
async def metrics_operator_leaderboard(
    limit: int = Query(default=10, ge=1, le=50),
    auth: dict = Depends(require_operator_or_admin),
):
    """Top operadores por trust_score + volumen mensual."""
    rows = await fetch_all(
        """
        SELECT u.id, u.alias, u.full_name,
               COALESCE(u.trust_score, 50) AS trust_score,
               u.kyc_status,
               COALESCE((
                   SELECT SUM(wl.amount_usdt) FROM wallet_ledger wl
                   WHERE wl.user_id = u.id AND wl.type = 'ORDER_PROFIT'
                     AND wl.created_at >= date_trunc('month', now())
               ), 0) AS profit_month,
               COALESCE((
                   SELECT COUNT(*) FROM orders o
                   WHERE o.operator_user_id = u.id AND o.status = 'PAGADA'
                     AND o.created_at >= date_trunc('month', now())
               ), 0) AS orders_month
        FROM users u
        WHERE u.role IN ('operator', 'admin')
          AND u.is_active = true
        ORDER BY u.trust_score DESC NULLS LAST, profit_month DESC
        LIMIT %s
        """,
        (limit,),
    )

    from decimal import Decimal

    def _s(v):
        if v is None:
            return None
        if isinstance(v, Decimal):
            return str(v.quantize(Decimal("0.01")))
        return v

    return {
        "leaderboard": [
            {
                "rank": idx + 1,
                "alias": r["alias"],
                "full_name": r.get("full_name") or r["alias"],
                "trust_score": float(r["trust_score"]),
                "profit_month": _s(r["profit_month"]),
                "orders_month": int(r["orders_month"]),
                "kyc_status": r.get("kyc_status") or "PENDING",
            }
            for idx, r in enumerate(rows or [])
        ]
    }


# ============================================================
# GET /metrics/company-overview
# ============================================================

@router.get("/metrics/export-orders")
def export_orders_metrics(
    days: int = Query(default=30, le=365),
    auth: dict = Depends(require_operator_or_admin)
):
    """Exporta órdenes en el periodo solicitado con foco en profit real."""
    wh, prm = _op_filter(auth)

    rows = fetch_all(
        f"""
        SELECT
            public_id,
            created_at,
            origin_country,
            dest_country,
            status,
            amount_origin,
            fiat_origin,
            payout_dest,
            dest_currency,
            profit_usdt,
            profit_real_usdt
        FROM orders
        WHERE created_at >= (CURRENT_DATE - (%s::int - 1) * INTERVAL '1 day')
        {wh}
        ORDER BY created_at DESC
        """,
        (days,) + prm,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Fecha", "País Origen", "País Destino", "Status",
        "Monto Origen", "Moneda Origen", "Payout Destino", "Moneda Destino",
        "Profit Teórico (USDT)", "Utilidad Neta (USDT)"
    ])

    for r in rows:
        writer.writerow([
            r["public_id"],
            r["created_at"].isoformat() if r["created_at"] else "",
            r["origin_country"],
            r["dest_country"],
            r["status"],
            round(float(r["amount_origin"] or 0), 2),
            r["fiat_origin"],
            round(float(r["payout_dest"] or 0), 2),
            r["dest_currency"],
            round(float(r["profit_usdt"] or 0), 2),
            round(float(r["profit_real_usdt"] or 0), 2)
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=export_ordenes_{days}d_{_date.today()}.csv"}
    )


@router.get("/metrics/company-overview")
async def metrics_company_overview(
    date_from: str | None = Query(None, description="YYYY-MM-DD"),
    date_to: str | None = Query(None, description="YYYY-MM-DD"),
    origin_country: str | None = Query(None),
    auth: dict = Depends(require_operator_or_admin),
):
    wh, prm = _op_filter(auth)
    admin = _is_admin(auth)

    # Build dynamic date/country filters
    extra_conditions = ""
    extra_params: list = []
    if date_from:
        extra_conditions += " AND created_at >= %s::timestamptz"
        extra_params.append(date_from)
    if date_to:
        extra_conditions += " AND created_at < (%s::date + interval '1 day')::timestamptz"
        extra_params.append(date_to)
    if origin_country:
        extra_conditions += " AND origin_country = %s"
        extra_params.append(origin_country.upper())

    combined_prm = prm + tuple(extra_params)

    # --- Query 1: conteos + profit ---
    row = await fetch_one(
        f"""
        SELECT
          COUNT(*) AS total_orders,
          COUNT(*) FILTER (WHERE status IN
              ('CREADA','ORIGEN_VERIFICANDO','ORIGEN_CONFIRMADO','EN_PROCESO')
          ) AS pending_orders,
          COUNT(*) FILTER (WHERE status='PAGADA') AS completed_orders,
          COALESCE(SUM(profit_usdt) FILTER (WHERE status='PAGADA'), 0) AS total_profit_usd,
          COALESCE(SUM(profit_real_usdt) FILTER (WHERE status='PAGADA'), 0) AS total_profit_real_usd,
          COALESCE(SUM(amount_origin) FILTER (WHERE status='PAGADA'), 0) AS total_volume_origin
        FROM orders
        WHERE 1=1 {wh} {extra_conditions}
        """,
        combined_prm,
    ) or {}

    # --- Query 2: volumen por dest_currency (siempre) ---
    v_rows = await fetch_all(
        f"""
        SELECT dest_currency, COALESCE(SUM(payout_dest),0) AS vol, COUNT(*) AS cnt
        FROM orders
        WHERE status='PAGADA' {wh} {extra_conditions}
        GROUP BY dest_currency
        ORDER BY vol DESC
        """,
        combined_prm,
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
    try:
        paid_usd_usdt = sum(
            float(r["vol"] or 0)
            for r in v_rows
            if r and r.get("dest_currency") in ("USD", "USDT")
        )
    except Exception:
        paid_usd_usdt = 0.0

    # --- Query 3: wallets SOLO admin (no se ejecuta para operadores) ---
    origin_wallets_data = None

    if admin:
        w_rows = await fetch_all(
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
            "total_volume_origin": float(row.get("total_volume_origin") or 0),
            "paid_by_dest_currency": paid_by_dest_currency,
        },
    }

# ============================================================
# GET /admin/metrics/vault
# ============================================================

@router.get("/admin/metrics/vault")
async def admin_metrics_vault(auth: dict = Depends(require_operator_or_admin)):
    """
    Motor Central de Bóveda (Vault Master).
    Calcula de manera transaccional:
    (Total Profit Histórico de órdenes PAGADA) - (Suma de retiros pagados a operadores)
    """
    if not _is_admin(auth):
        raise HTTPException(status_code=403, detail="Solo administradores pueden ver la bóveda central")

    # Profit Total de órdenes (Ganancia bruta)
    # FILTRO: IN ('PAGADA', 'COMPLETADA') (estados confirmados en producción que contienen profit;
    # 'COMPLETADA' concentra el histórico actual, se mantiene 'PAGADA' por prudencia).
    row_profit = await fetch_one(
        "SELECT COALESCE(SUM(profit_real_usdt), 0) AS total_profit FROM orders WHERE status IN ('PAGADA', 'COMPLETADA')"
    )
    total_profit = float(row_profit["total_profit"]) if row_profit else 0.0

    # Retiros Totales pagados a operadores.
    # Filtra por status = 'RESUELTA' (único estado de retiro pagado observado en validación
    # de producción al momento de este fix; revisar si se agregan nuevos estados en el futuro).
    row_withdraw = await fetch_one(
        "SELECT COALESCE(SUM(amount_usdt), 0) AS total_withdrawals FROM withdrawals WHERE status = 'RESUELTA'"
    )
    total_withdrawals = float(row_withdraw["total_withdrawals"]) if row_withdraw else 0.0

    vault_balance = total_profit - total_withdrawals

    import datetime
    return {
        "ok": True,
        "vault_balance": vault_balance,
        "total_profit": total_profit,
        "total_withdrawals": total_withdrawals,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    }


# ============================================================
# GET /admin/metrics/treasury  (SM-101)
# ============================================================

@router.get("/admin/metrics/treasury")
async def admin_metrics_treasury(auth: dict = Depends(require_operator_or_admin)):
    """
    Vista financiera separada en conceptos canónicos.
    Solo lectura. No modifica datos.
    Ver FINANCIAL_MODEL.md para definiciones exactas.
    """
    if not _is_admin(auth):
        raise HTTPException(status_code=403, detail="Solo administradores pueden ver la tesorería")

    row_gp = await fetch_one(
        "SELECT COALESCE(SUM(profit_real_usdt), 0) AS v FROM orders WHERE status IN ('PAGADA', 'COMPLETADA')"
    )
    gross_profit = float(row_gp["v"]) if row_gp else 0.0

    row_oc = await fetch_one(
        "SELECT COALESCE(SUM(amount_usdt), 0) AS v FROM wallet_ledger WHERE type = 'ORDER_PROFIT'"
    )
    operator_commissions = float(row_oc["v"]) if row_oc else 0.0

    row_ol = await fetch_one(
        "SELECT COALESCE(SUM(balance_usdt), 0) AS v FROM wallets"
    )
    operator_liabilities = float(row_ol["v"]) if row_ol else 0.0

    row_rp = await fetch_one(
        "SELECT COALESCE(SUM(amount_usdt), 0) AS v FROM withdrawals WHERE status = 'RESUELTA'"
    )
    resolved_payouts = float(row_rp["v"]) if row_rp else 0.0

    business_retained_profit = gross_profit - operator_commissions

    withdrawal_coverage_estimate = None
    if operator_liabilities > 0:
        withdrawal_coverage_estimate = round(
            (gross_profit - resolved_payouts) / operator_liabilities, 4
        )

    import datetime
    return {
        "ok": True,
        "gross_profit": round(gross_profit, 2),
        "operator_commissions": round(operator_commissions, 2),
        "operator_liabilities": round(operator_liabilities, 2),
        "resolved_payouts": round(resolved_payouts, 2),
        "business_retained_profit": round(business_retained_profit, 2),
        "withdrawal_coverage_estimate": withdrawal_coverage_estimate,
        "disclaimer": "Estimación interna basada en registros de BD. No representa conciliación de caja externa.",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    }


# ============================================================
# GET /admin/metrics/daily_snapshot (SM-106)
# ============================================================

@router.get("/admin/metrics/daily_snapshot")
async def admin_metrics_daily_snapshot(
    date: str = Query(..., description="YYYY-MM-DD"),
    auth: dict = Depends(require_operator_or_admin)
):
    """
    SM-106: Daily financial snapshot.
    Minimalista, admin-only, solo lectura.
    """
    if not _is_admin(auth):
        raise HTTPException(status_code=403, detail="Solo administradores pueden ver el daily snapshot")

    row_orders = await fetch_one(
        """
        SELECT 
            COUNT(*) as orders_completed,
            COALESCE(SUM(payout_dest) FILTER (WHERE dest_currency IN ('USD', 'USDT')), 0) as volume_usd,
            COALESCE(SUM(profit_real_usdt), 0) as gross_profit_today
        FROM orders
        WHERE status IN ('PAGADA', 'COMPLETADA')
          AND updated_at >= %s::date
          AND updated_at < (%s::date + interval '1 day')
        """,
        (date, date)
    )
    orders_completed = int(row_orders["orders_completed"] or 0) if row_orders else 0
    volume_usd = float(row_orders["volume_usd"] or 0.0) if row_orders else 0.0
    gross_profit_today = float(row_orders["gross_profit_today"] or 0.0) if row_orders else 0.0

    row_commissions = await fetch_one(
        """
        SELECT COALESCE(SUM(amount_usdt), 0) as commissions_today
        FROM wallet_ledger
        WHERE type = 'ORDER_PROFIT'
          AND created_at >= %s::date
          AND created_at < (%s::date + interval '1 day')
        """,
        (date, date)
    )
    commissions_today = float(row_commissions["commissions_today"] or 0.0) if row_commissions else 0.0

    net_retained_today = gross_profit_today - commissions_today

    row_payouts = await fetch_one(
        """
        SELECT COALESCE(SUM(amount_usdt), 0) as payouts_today
        FROM withdrawals
        WHERE status = 'RESUELTA'
          AND updated_at >= %s::date
          AND updated_at < (%s::date + interval '1 day')
        """,
        (date, date)
    )
    payouts_today = float(row_payouts["payouts_today"] or 0.0) if row_payouts else 0.0

    row_new_req = await fetch_one(
        """
        SELECT COUNT(*) as new_withdrawal_requests
        FROM withdrawals
        WHERE status = 'SOLICITADA'
          AND created_at >= %s::date
          AND created_at < (%s::date + interval '1 day')
        """,
        (date, date)
    )
    new_withdrawal_requests = int(row_new_req["new_withdrawal_requests"] or 0) if row_new_req else 0

    return {
        "date": date,
        "orders_completed": orders_completed,
        "volume_usd": round(volume_usd, 2),
        "gross_profit_today": round(gross_profit_today, 2),
        "commissions_today": round(commissions_today, 2),
        "net_retained_today": round(net_retained_today, 2),
        "payouts_today": round(payouts_today, 2),
        "new_withdrawal_requests": new_withdrawal_requests,
        "disclaimer": "Estimación interna basada en registros de BD. Total volumen refleja pagos procesados en USD/USDT. No representa conciliación de caja externa."
    }

# ============================================================
# GET /metrics/control-center (AGREGADOR FASE 3)
# ============================================================

@router.get("/metrics/control-center")
async def metrics_control_center(auth: dict = Depends(require_operator_or_admin)):
    """
    Agregador Maestro (M10 hardened).
    Combina Overview, Vault y Leaderboard en un solo payload para el Admin.
    Reduce latencia y número de peticiones desde el frontend.
    """
    import asyncio
    import datetime

    # Ejecutar llamadas concurrentes para máxima eficiencia
    tasks = [
        metrics_overview(auth),
        metrics_operator_leaderboard(limit=5, auth=auth)
    ]
    
    # Solo admin ve la bóveda central
    if _is_admin(auth):
        tasks.append(admin_metrics_vault(auth))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    overview_res = results[0] if not isinstance(results[0], Exception) else {}
    leaderboard_res = results[1] if not isinstance(results[1], Exception) else {"leaderboard": []}
    
    vault_res = None
    if _is_admin(auth) and len(results) > 2:
        vault_res = results[2] if not isinstance(results[2], Exception) else None

    return {
        "ok": True,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "data": {
            "overview": overview_res,
            "leaderboard": leaderboard_res.get("leaderboard", []),
            "vault": vault_res,
            "config": {
                "role": auth.get("role"),
                "is_admin": _is_admin(auth)
            }
        }
    }
