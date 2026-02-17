import pathlib

orders_code = '''"""Router: Ordenes y Trades"""

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from ..db import fetch_one, fetch_all
from ..auth import verify_api_key

router = APIRouter(tags=["orders"])


def _operator_filter(auth: dict):
    if auth.get("role") in ("admin", "ADMIN") or auth.get("auth") == "api_key":
        return "", ()
    user_id = auth.get("user_id")
    if not user_id:
        raise HTTPException(status_code=403, detail="user_id no encontrado en token")
    return " AND o.operator_user_id = %s", (user_id,)


@router.get("/orders")
def list_orders(limit: int = Query(default=20, le=100), auth: dict = Depends(verify_api_key)):
    where_extra, params_extra = _operator_filter(auth)
    rows = fetch_all(
        f"""
        SELECT
          o.public_id, o.created_at, o.status, o.awaiting_paid_proof,
          o.origin_country, o.dest_country,
          o.amount_origin, o.payout_dest, o.profit_usdt,
          o.awaiting_paid_proof_at, o.paid_at, o.updated_at
        FROM orders o
        WHERE 1=1 {where_extra}
        ORDER BY o.created_at DESC
        LIMIT %s
        """,
        params_extra + (limit,),
    )
    orders = []
    for r in rows:
        orders.append({
            "public_id": r["public_id"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "status": r["status"],
            "awaiting_paid_proof": bool(r["awaiting_paid_proof"]),
            "origin_country": r["origin_country"],
            "dest_country": r["dest_country"],
            "amount_origin": float(r["amount_origin"]) if r["amount_origin"] is not None else None,
            "payout_dest": float(r["payout_dest"]) if r["payout_dest"] is not None else None,
            "profit_usdt": float(r["profit_usdt"]) if r["profit_usdt"] is not None else None,
            "awaiting_paid_proof_at": r["awaiting_paid_proof_at"].isoformat() if r["awaiting_paid_proof_at"] else None,
            "paid_at": r["paid_at"].isoformat() if r["paid_at"] else None,
            "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None,
        })
    return {"count": len(orders), "orders": orders}


@router.get("/orders/{public_id}")
def order_detail(public_id: int, auth: dict = Depends(verify_api_key)):
    where_extra, params_extra = _operator_filter(auth)
    order = fetch_one(
        f"SELECT * FROM orders o WHERE o.public_id=%s {where_extra} LIMIT 1",
        (public_id,) + params_extra,
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    ledger_rows = fetch_all(
        """
        SELECT user_id, amount_usdt, type, ref_order_public_id, memo, created_at
        FROM wallet_ledger
        WHERE ref_order_public_id=%s
        ORDER BY created_at ASC
        """,
        (public_id,),
    )
    ledger = []
    for r in ledger_rows:
        ledger.append({
            "user_id": r["user_id"],
            "amount_usdt": float(r["amount_usdt"]) if r["amount_usdt"] is not None else None,
            "type": r["type"],
            "ref_order_public_id": r["ref_order_public_id"],
            "memo": r["memo"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        })

    trows = fetch_all(
        """
        SELECT id, side, fiat_currency, fiat_amount, price, usdt_amount, fee_usdt, source, external_ref, note, created_at
        FROM order_trades
        WHERE order_public_id=%s
        ORDER BY created_at ASC, id ASC
        """,
        (public_id,),
    )
    trades = []
    buy_usdt = 0.0
    sell_usdt = 0.0
    fee_total = 0.0
    for r in trows:
        usdt = float(r["usdt_amount"] or 0)
        fee = float(r["fee_usdt"] or 0) if r["fee_usdt"] is not None else 0.0
        side = (r["side"] or "").upper()
        if side == "BUY":
            buy_usdt += usdt
            fee_total += fee
        elif side == "SELL":
            sell_usdt += usdt
            fee_total += fee
        trades.append({
            "id": int(r["id"]),
            "side": side,
            "fiat_currency": r["fiat_currency"],
            "fiat_amount": float(r["fiat_amount"]),
            "price": float(r["price"]) if r["price"] is not None else None,
            "usdt_amount": usdt,
            "fee_usdt": fee,
            "source": r["source"],
            "external_ref": r["external_ref"],
            "note": r["note"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        })
    profit_real_usdt = (buy_usdt - sell_usdt) - fee_total
    return {
        "order": order,
        "ledger": ledger,
        "trades": trades,
        "profit_real_usdt": profit_real_usdt,
        "profit_real_breakdown": {
            "buy_usdt": buy_usdt,
            "sell_usdt": sell_usdt,
            "fees_usdt": fee_total,
        },
    }


class OrderTradeIn(BaseModel):
    side: str
    fiat_currency: str
    fiat_amount: float
    price: float | None = None
    usdt_amount: float
    fee_usdt: float | None = None
    source: str | None = None
    external_ref: str | None = None
    note: str | None = None


@router.get("/orders/{public_id}/trades")
def get_order_trades(public_id: int, auth: dict = Depends(verify_api_key)):
    rows = fetch_all(
        """
        SELECT id, order_public_id, side, fiat_currency, fiat_amount, price, usdt_amount, fee_usdt,
               source, external_ref, note, created_at, created_by_user_id
        FROM order_trades
        WHERE order_public_id=%s
        ORDER BY created_at ASC, id ASC
        """,
        (public_id,),
    )
    out = []
    for r in rows:
        out.append({
            "id": int(r["id"]),
            "order_public_id": int(r["order_public_id"]),
            "side": r["side"],
            "fiat_currency": r["fiat_currency"],
            "fiat_amount": float(r["fiat_amount"]),
            "price": float(r["price"]) if r["price"] is not None else None,
            "usdt_amount": float(r["usdt_amount"]),
            "fee_usdt": float(r["fee_usdt"]) if r["fee_usdt"] is not None else None,
            "source": r["source"],
            "external_ref": r["external_ref"],
            "note": r["note"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "created_by_user_id": r["created_by_user_id"],
        })
    return {"ok": True, "public_id": public_id, "items": out}


@router.post("/orders/{public_id}/trades")
def create_order_trade(public_id: int, payload: OrderTradeIn, auth: dict = Depends(verify_api_key)):
    side = (payload.side or "").upper().strip()
    if side not in ("BUY", "SELL"):
        raise HTTPException(status_code=400, detail="side must be BUY or SELL")
    row = fetch_one(
        """
        INSERT INTO order_trades (
          order_public_id, side, fiat_currency, fiat_amount, price, usdt_amount, fee_usdt,
          source, external_ref, note, created_by_user_id
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NULL)
        RETURNING id
        """,
        (
            public_id, side, payload.fiat_currency, payload.fiat_amount,
            payload.price, payload.usdt_amount, payload.fee_usdt,
            payload.source, payload.external_ref, payload.note,
        ),
        rw=True,
    )
    agg = fetch_one(
        """
        SELECT
          COALESCE(SUM(CASE WHEN side='BUY' THEN usdt_amount ELSE 0 END),0) AS buy_usdt,
          COALESCE(SUM(CASE WHEN side='SELL' THEN usdt_amount ELSE 0 END),0) AS sell_usdt,
          COALESCE(SUM(COALESCE(fee_usdt,0)),0) AS fees_usdt
        FROM order_trades
        WHERE order_public_id=%s
        """,
        (public_id,),
    )
    buy_usdt = float(agg["buy_usdt"] or 0) if agg else 0.0
    sell_usdt = float(agg["sell_usdt"] or 0) if agg else 0.0
    fees_usdt = float(agg["fees_usdt"] or 0) if agg else 0.0
    profit_real = (buy_usdt - sell_usdt) - fees_usdt
    fetch_one(
        "UPDATE orders SET profit_real_usdt=%s WHERE public_id=%s RETURNING public_id",
        (profit_real, public_id),
        rw=True,
    )
    return {"ok": True, "id": int(row["id"]) if row else None}
'''

metrics_code = '''"""Router: Metricas y Dashboard"""

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
'''

pathlib.Path("backoffice_api/app/routers/orders.py").write_text(orders_code, encoding="utf-8")
pathlib.Path("backoffice_api/app/routers/metrics.py").write_text(metrics_code, encoding="utf-8")
print("orders.py OK")
print("metrics.py OK")
