"""Router: Metricas y Dashboard"""

# Estados de órdenes (fuente única)
ST_CREADA = "CREADA"
ST_ORIGEN = "ORIGEN_VERIFICANDO"
ST_PROCESO = "EN_PROCESO"
ST_PAGADA = "PAGADA"
ST_CANCELADA = "CANCELADA"

from fastapi import APIRouter, Depends, Query
from ..db import fetch_one, fetch_all
from ..auth import verify_api_key

router = APIRouter(tags=["metrics"])


def _op_filter(auth: dict):
    if auth.get("role") in ("admin", "ADMIN") or auth.get("auth") == "api_key":
        return "", ()
    user_id = auth.get("user_id")
    if not user_id:
        return "", ()
    return " AND operator_user_id = %s", (user_id,)


@router.get("/metrics/overview")
def metrics_overview(auth: dict = Depends(verify_api_key)):
    wh, prm = _op_filter(auth)
    row = fetch_one(
        f"""
        SELECT
          COUNT(*) FILTER (WHERE status='CREADA') AS creadas,
          COUNT(*) FILTER (WHERE status='ORIGEN_VERIFICANDO') AS origen_verificando,
          COUNT(*) FILTER (WHERE status='EN_PROCESO') AS en_proceso,
          COUNT(*) FILTER (WHERE status='PAGADA') AS pagadas,
          COUNT(*) FILTER (WHERE status='CANCELADA') AS canceladas,
          COUNT(*) FILTER (WHERE awaiting_paid_proof=true) AS awaiting_paid_proof,
          COALESCE(SUM(profit_usdt) FILTER (WHERE status='PAGADA'), 0) AS total_profit_usd,
          COALESCE(SUM(profit_real_usdt) FILTER (WHERE status='PAGADA'), 0) AS total_profit_real_usd,
          0::numeric AS total_volume_usd
        FROM orders
        WHERE 1=1 {wh}
        """,
        prm,
    )
    creadas = int(row["creadas"] or 0)
    origen_verificando = int(row["origen_verificando"] or 0)
    en_proceso = int(row["en_proceso"] or 0)
    pagadas = int(row["pagadas"] or 0)
    canceladas = int(row["canceladas"] or 0)
    return {
        "total_orders": creadas + origen_verificando + en_proceso + pagadas + canceladas,
        "pending_orders": creadas + origen_verificando + en_proceso,
        "completed_orders": pagadas,
        "total_volume_usd": float(row["total_volume_usd"] or 0),
        "total_profit_usd": float(row["total_profit_usd"] or 0),
        "total_profit_real_usd": float(row["total_profit_real_usd"] or 0),
        "status_counts": {
            "CREADA": creadas,
            "ORIGEN_VERIFICANDO": origen_verificando,
            "EN_PROCESO": en_proceso,
            "PAGADA": pagadas,
            "CANCELADA": canceladas,
        },
        "awaiting_paid_proof": int(row["awaiting_paid_proof"] or 0),
    }


@router.get("/metrics/profit_daily")
def profit_daily(days: int = Query(default=30, le=90), auth: dict = Depends(verify_api_key)):
    from ..audit import get_profit_daily
    data = get_profit_daily(days)
    return {"days": days, "profit_by_day": data}


@router.get("/operators/ranking")
def operators_ranking(days: int = Query(default=7, le=90), auth: dict = Depends(verify_api_key)):
    from ..audit import get_operators_ranking
    data = get_operators_ranking(days)
    return {"ok": True, "days": days, "operators": data}


@router.get("/metrics/corridors")
def metrics_corridors(days: int = Query(default=30, le=90), auth: dict = Depends(verify_api_key)):
    from ..audit import get_corridors
    data = get_corridors(days)
    return {"ok": True, "days": days, "corridors": data}


@router.get("/metrics/p2p-prices")
def metrics_p2p_prices(
    country: str = Query(default=None),
    limit: int = Query(default=20, le=100),
    auth: dict = Depends(verify_api_key),
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
            (country.upper(), limit),
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
            """,
        )

    def iso(x):
        return x.isoformat() if x else None

    items = []
    for r in rows:
        buy = float(r["buy_price"]) if r["buy_price"] is not None else None
        sell = float(r["sell_price"]) if r["sell_price"] is not None else None
        spread = None
        if buy and sell and sell > 0:
            spread = round(((buy - sell) / sell) * 100, 4)
        items.append({
            "country": r["country"],
            "fiat": r["fiat"],
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


@router.get("/metrics/company-overview")
def metrics_company_overview(auth: dict = Depends(verify_api_key)):
    wh, prm = _op_filter(auth)
    row = fetch_one(
        f"""
        SELECT
          COUNT(*) AS total_orders,
          COUNT(*) FILTER (WHERE status IN ('CREADA','ORIGEN_VERIFICANDO','EN_PROCESO')) AS pending_orders,
          COUNT(*) FILTER (WHERE status='PAGADA') AS completed_orders,
          COALESCE(SUM(profit_usdt) FILTER (WHERE status='PAGADA'), 0) AS total_profit_usd,
          COALESCE(SUM(profit_real_usdt) FILTER (WHERE status='PAGADA'), 0) AS total_profit_real_usd
        FROM orders
        WHERE 1=1 {wh}
        """,
        prm,
    )

    w = fetch_all(
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
        """
    )

    wallets = []
    pending_by_currency = {}
    for r in w:
        bal = float(r["current_balance"] or 0)
        cur = r["fiat_currency"]
        wallets.append({
            "origin_country": r["origin_country"],
            "fiat_currency": cur,
            "current_balance": bal,
        })
        if bal > 0:
            if cur not in pending_by_currency:
                pending_by_currency[cur] = 0.0
            pending_by_currency[cur] += bal

    top_pending = sorted(
        [x for x in wallets if x["current_balance"] > 0],
        key=lambda x: x["current_balance"],
        reverse=True,
    )[:10]

    v_rows = fetch_all(
        f"""
        SELECT dest_currency, COALESCE(SUM(payout_dest),0) AS vol, COUNT(*) AS cnt
        FROM orders
        WHERE status='PAGADA' {wh}
        GROUP BY dest_currency
        ORDER BY vol DESC
        """,
        prm,
    )
    paid_by_dest_currency = [
        {
            "dest_currency": r["dest_currency"],
            "volume": float(r["vol"] or 0),
            "count": int(r["cnt"] or 0),
        }
        for r in v_rows
        if r["dest_currency"] is not None
    ]

    v_row = fetch_one(
        f"""
        SELECT COALESCE(SUM(payout_dest), 0) AS vol
        FROM orders
        WHERE status='PAGADA' AND dest_currency IN ('USD','USDT') {wh}
        """,
        prm,
    )
    paid_usd_usdt = float(v_row["vol"] or 0) if v_row else 0.0

    return {
        "ok": True,
        "orders": {
            "total_orders": int(row["total_orders"] or 0) if row else 0,
            "pending_orders": int(row["pending_orders"] or 0) if row else 0,
            "completed_orders": int(row["completed_orders"] or 0) if row else 0,
        },
        "profit": {
            "total_profit_usd": float(row["total_profit_usd"] or 0) if row else 0.0,
            "total_profit_real_usd": float(row["total_profit_real_usd"] or 0) if row else 0.0,
        },
        "origin_wallets": {
            "pending_by_currency": pending_by_currency,
            "top_pending": top_pending,
        },
        "volume": {
            "paid_usd_usdt": paid_usd_usdt,
            "paid_by_dest_currency": paid_by_dest_currency,
        },
    }
