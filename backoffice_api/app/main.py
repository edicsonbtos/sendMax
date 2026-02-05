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
    orders = fetch_all(
        """
        SELECT
          public_id, created_at, status, awaiting_paid_proof,
          origin_country, destination_country, amount_origin, amount_destination,
          destination_type, beneficiary
        FROM orders
        ORDER BY created_at DESC
        LIMIT %s
        """,
        (limit,)
    )
    return {"orders": orders}

@app.get("/orders/{public_id}")
def order_detail(public_id: str, api_key: str = Depends(verify_api_key)):
    order = fetch_one(
        "SELECT * FROM orders WHERE public_id=%s",
        (public_id,)
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    ledger = fetch_all(
        """
        SELECT * FROM ledger
        WHERE order_id=%s
        ORDER BY created_at ASC
        """,
        (order["id"],)
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
