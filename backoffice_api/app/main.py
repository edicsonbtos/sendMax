from fastapi import FastAPI, Query, Request, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
import os
from .db import fetch_one, fetch_all

app = FastAPI(title="Sendmax Backoffice API", version="0.5.1")

# Configuración de API Key
API_KEY = os.getenv("BACKOFFICE_API_KEY", "dev-key-12345")
api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)

async def verify_api_key(api_key: str = Depends(api_key_header)):
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-KEY header"
        )
    if api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return api_key

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["X-API-KEY"],
)

@app.get("/health")
def health():
    return {"ok": True, "service": "backoffice-api", "version": "0.5.1"}

@app.get("/metrics/overview")
def metrics_overview(api_key: str = Depends(verify_api_key)):
    row = fetch_one(
        """
        SELECT
          COUNT(*) FILTER (WHERE status='CREADA')      AS creadas,
          COUNT(*) FILTER (WHERE status='EN_PROCESO')  AS en_proceso,
          COUNT(*) FILTER (WHERE status='PAGADA')      AS pagadas,
          COUNT(*) FILTER (WHERE status='CANCELADA')   AS canceladas,
          COUNT(*) FILTER (WHERE awaiting_paid_proof=true) AS awaiting_paid_proof
        FROM orders
        """
    )
    return {
        "status_counts": {
            "CREADA": row["creadas"],
            "EN_PROCESO": row["en_proceso"],
            "PAGADA": row["pagadas"],
            "CANCELADA": row["canceladas"],
        },
        "awaiting_paid_proof": row["awaiting_paid_proof"]
    }

@app.get("/orders")
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
        orders.append(
            {
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
            }
        )
    return {"count": len(orders), "orders": orders}

@app.get("/orders/{public_id}")
def order_detail(public_id: int, api_key: str = Depends(verify_api_key)):
    order = fetch_one(
        """
        SELECT *
        FROM orders
        WHERE public_id=%s
        LIMIT 1
        """,
        (public_id,),
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
        ledger.append(
            {
                "user_id": r["user_id"],
                "amount_usdt": float(r["amount_usdt"]) if r["amount_usdt"] is not None else None,
                "type": r["type"],
                "ref_order_public_id": r["ref_order_public_id"],
                "memo": r["memo"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
        )

    return {"order": order, "ledger": ledger}

@app.get("/metrics/profit_daily")
def profit_daily(days: int = Query(default=30, le=90), api_key: str = Depends(verify_api_key)):
    from .audit import get_profit_daily
    data = get_profit_daily(days)
    return {"days": days, "profit_by_day": data}

@app.get("/alerts/stuck")
def alerts_stuck(api_key: str = Depends(verify_api_key)):
    from .audit import get_stuck_orders
    return get_stuck_orders()

@app.get("/operators/ranking")
def operators_ranking(days: int = Query(default=7, le=30), api_key: str = Depends(verify_api_key)):
    from .audit import get_operators_ranking
    data = get_operators_ranking(days)
    return {"days": days, "operators": data}
