"""Router: Órdenes y Trades"""

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from ..db import fetch_one, fetch_all
from ..auth import verify_api_key

router = APIRouter(tags=["orders"])


@router.get("/orders")
def list_orders(limit: int = Query(default=20, le=100), api_key: str = Depends(verify_api_key)):
    rows = fetch_all(
        """
        SELECT
          public_id, created_at, status, awaiting_paid_proof,
          origin_country, dest_country,
          amount_origin, payout_dest, profit_usdt,
          awaiting_paid_proof_at, paid_at, updated_at
        FROM orders
        ORDER BY created_at DESC
        LIMIT %s
        """,
        (limit,),
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
def order_detail(public_id: int, api_key: str = Depends(verify_api_key)):
    order = fetch_one("SELECT * FROM orders WHERE public_id=%s LIMIT 1", (public_id,))
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
def get_order_trades(public_id: int, api_key: str = Depends(verify_api_key)):
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
def create_order_trade(public_id: int, payload: OrderTradeIn, api_key: str = Depends(verify_api_key)):
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
