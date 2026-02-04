from fastapi import FastAPI, Query
import os
from .db import fetch_one, fetch_all

app = FastAPI(title="Sendmax Backoffice API", version="0.4.0")

@app.get("/health")
def health():
    return {"ok": True, "service": "backoffice-api"}

@app.get("/metrics/overview")
def metrics_overview():
    row = fetch_one(
        """
        SELECT
          COUNT(*) FILTER (WHERE status='CREADA')      AS creadas,
          COUNT(*) FILTER (WHERE status='EN_PROCESO')  AS en_proceso,
          COUNT(*) FILTER (WHERE status='PAGADA')      AS pagadas,
          COUNT(*) FILTER (WHERE status='CANCELADA')   AS canceladas,
          COUNT(*) FILTER (WHERE awaiting_paid_proof=true) AS awaiting_paid_proof
        FROM orders;
        """
    )
    return {
        "ok": True,
        "data": {
            "creadas": row[0] if row else 0,
            "en_proceso": row[1] if row else 0,
            "pagadas": row[2] if row else 0,
            "canceladas": row[3] if row else 0,
            "awaiting_paid_proof": row[4] if row else 0,
        },
        "env": os.getenv("ENV", "local"),
    }

@app.get("/orders")
def list_orders(limit: int = Query(20, ge=1, le=200)):
    rows = fetch_all(
        """
        SELECT public_id, status, origin_country, dest_country,
               amount_origin, payout_dest, profit_usdt,
               awaiting_paid_proof, awaiting_paid_proof_at,
               created_at, updated_at
        FROM orders
        ORDER BY created_at DESC
        LIMIT %s;
        """,
        (limit,),
    )

    data = []
    for r in rows:
        data.append(
            {
                "public_id": r[0],
                "status": r[1],
                "origin_country": r[2],
                "dest_country": r[3],
                "amount_origin": float(r[4]) if r[4] is not None else None,
                "payout_dest": float(r[5]) if r[5] is not None else None,
                "profit_usdt": float(r[6]) if r[6] is not None else None,
                "awaiting_paid_proof": bool(r[7]),
                "awaiting_paid_proof_at": r[8].isoformat() if r[8] else None,
                "created_at": r[9].isoformat() if r[9] else None,
                "updated_at": r[10].isoformat() if r[10] else None,
            }
        )

    return {"ok": True, "count": len(data), "data": data}

@app.get("/orders/{public_id}")
def get_order(public_id: int):
    o = fetch_one(
        """
        SELECT public_id, status, operator_user_id,
               origin_country, dest_country,
               amount_origin, payout_dest, profit_usdt,
               beneficiary_text,
               origin_payment_proof_file_id, dest_payment_proof_file_id,
               awaiting_paid_proof, awaiting_paid_proof_at, awaiting_paid_proof_by,
               paid_at, cancel_reason,
               created_at, updated_at
        FROM orders
        WHERE public_id=%s
        LIMIT 1;
        """,
        (public_id,),
    )
    if not o:
        return {"ok": False, "error": "ORDER_NOT_FOUND"}

    order = {
        "public_id": o[0],
        "status": o[1],
        "operator_user_id": o[2],
        "origin_country": o[3],
        "dest_country": o[4],
        "amount_origin": float(o[5]) if o[5] is not None else None,
        "payout_dest": float(o[6]) if o[6] is not None else None,
        "profit_usdt": float(o[7]) if o[7] is not None else None,
        "beneficiary_text": o[8],
        "origin_payment_proof_file_id": o[9],
        "dest_payment_proof_file_id": o[10],
        "awaiting_paid_proof": bool(o[11]),
        "awaiting_paid_proof_at": o[12].isoformat() if o[12] else None,
        "awaiting_paid_proof_by": o[13],
        "paid_at": o[14].isoformat() if o[14] else None,
        "cancel_reason": o[15],
        "created_at": o[16].isoformat() if o[16] else None,
        "updated_at": o[17].isoformat() if o[17] else None,
    }

    # Ledger asociado a la orden (si tu tabla tiene created_at; si no, lo ajustamos)
    rows = fetch_all(
        """
        SELECT user_id, amount_usdt, type, ref_order_public_id, memo, created_at
        FROM wallet_ledger
        WHERE ref_order_public_id=%s
        ORDER BY created_at ASC;
        """,
        (public_id,),
    )
    ledger = []
    for r in rows:
        ledger.append(
            {
                "user_id": r[0],
                "amount_usdt": float(r[1]) if r[1] is not None else None,
                "type": r[2],
                "ref_order_public_id": r[3],
                "memo": r[4],
                "created_at": r[5].isoformat() if r[5] else None,
            }
        )

    return {"ok": True, "order": order, "ledger": ledger}
