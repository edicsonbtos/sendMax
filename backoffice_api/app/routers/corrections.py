"""Router: Correccion manual de profit y datos de ejecucion"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ..db import fetch_one
from ..auth import require_admin

router = APIRouter(tags=["corrections"])


class ProfitCorrectionIn(BaseModel):
    execution_price_buy: float | None = None
    execution_price_sell: float | None = None
    profit_real_usdt: float | None = None
    note: str | None = None


@router.get("/orders/{public_id}/execution")
def get_execution_data(public_id: int, auth: dict = Depends(require_admin)):
    row = fetch_one(
        """
        SELECT public_id, amount_origin, payout_dest, rate_client,
               commission_pct, profit_usdt, profit_real_usdt,
               execution_price_buy, execution_price_sell,
               correction_note,
               origin_country, dest_country, status, paid_at
        FROM orders WHERE public_id=%s LIMIT 1
        """,
        (public_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"ok": True, "order": row}


@router.put("/orders/{public_id}/execution")
def update_execution_data(public_id: int, payload: ProfitCorrectionIn, auth: dict = Depends(require_admin)):

    order = fetch_one("SELECT public_id, status FROM orders WHERE public_id=%s", (public_id,))
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    updates = []
    params = []

    if payload.execution_price_buy is not None:
        updates.append("execution_price_buy = %s")
        params.append(payload.execution_price_buy)

    if payload.execution_price_sell is not None:
        updates.append("execution_price_sell = %s")
        params.append(payload.execution_price_sell)

    if payload.profit_real_usdt is not None:
        updates.append("profit_real_usdt = %s")
        params.append(payload.profit_real_usdt)

    if payload.note is not None:
        updates.append("correction_note = %s")
        params.append(payload.note)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates.append("updated_at = now()")
    params.append(public_id)

    sql = f"UPDATE orders SET {', '.join(updates)} WHERE public_id = %s RETURNING public_id"
    result = fetch_one(sql, tuple(params), rw=True)

    return {"ok": True, "public_id": public_id, "updated_fields": len(updates) - 1}