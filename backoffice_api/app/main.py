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
from datetime import datetime, date, timedelta, timezone
from fastapi import Query

# --- Daily close (Venezuela UTC-4) ---
VET = timezone(timedelta(hours=-4))

@app.get("/daily-close")
def daily_close(
    day: str = Query(..., description="YYYY-MM-DD en hora Venezuela"),
    api_key: str = Depends(verify_api_key),
):
    try:
        d = date.fromisoformat(day)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid day format. Use YYYY-MM-DD")

    start_local = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=VET)
    end_local = start_local + timedelta(days=1)

    # Convertimos a UTC para comparar con created_at (timestamptz)
    start_utc = start_local.astimezone(timezone.utc)
    end_utc = end_local.astimezone(timezone.utc)

    # 1) Conteo por status
    row = fetch_one(
        """
        SELECT
          COUNT(*) FILTER (WHERE status='CREADA') AS creadas,
          COUNT(*) FILTER (WHERE status='ORIGEN_VERIFICANDO') AS origen_verificando,
          COUNT(*) FILTER (WHERE status='ORIGEN_CONFIRMADO') AS origen_confirmado,
          COUNT(*) FILTER (WHERE status='EN_PROCESO') AS en_proceso,
          COUNT(*) FILTER (WHERE status='PAGADA') AS pagadas,
          COUNT(*) FILTER (WHERE status='CANCELADA') AS canceladas,
          COUNT(*) FILTER (WHERE awaiting_paid_proof=true) AS awaiting_paid_proof
        FROM orders
        WHERE created_at >= %s AND created_at < %s
        """,
        (start_utc, end_utc),
    )

    # 2) Profit del día (solo pagadas)
    row2 = fetch_one(
        """
        SELECT COALESCE(SUM(profit_usdt), 0) AS profit_usdt
        FROM orders
        WHERE status='PAGADA'
          AND paid_at >= %s AND paid_at < %s
        """,
        (start_utc, end_utc),
    )

    # 3) Volumen por origen (monto origen fiat)
    rows3 = fetch_all(
        """
        SELECT origin_country, COALESCE(SUM(amount_origin),0) AS total_amount_origin
        FROM orders
        WHERE created_at >= %s AND created_at < %s
        GROUP BY origin_country
        ORDER BY total_amount_origin DESC
        """,
        (start_utc, end_utc),
    )

    by_origin = []
    for r in rows3:
        by_origin.append({"origin_country": r["origin_country"], "amount_origin_sum": float(r["total_amount_origin"])})

    return {
        "ok": True,
        "day_local": day,
        "tz": "VET(UTC-4)",
        "window_utc": {"start": start_utc.isoformat(), "end": end_utc.isoformat()},
        "status_counts": dict(row) if row else {},
        "profit_usdt_paid_window": float(row2["profit_usdt"]) if row2 else 0.0,
        "volume_by_origin_amount_origin": by_origin,
    }
from datetime import datetime, timedelta, timezone

@app.get("/alerts/stuck-30m")
def alerts_stuck_30m(api_key: str = Depends(verify_api_key)):
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=30)

    origin_rows = fetch_all(
        """
        SELECT public_id, origin_country, dest_country, status, created_at, updated_at
        FROM orders
        WHERE status='ORIGEN_VERIFICANDO'
          AND created_at < %s
        ORDER BY created_at ASC
        LIMIT 100
        """,
        (cutoff,),
    )

    pay_rows = fetch_all(
        """
        SELECT public_id, origin_country, dest_country, status,
               awaiting_paid_proof_at, updated_at
        FROM orders
        WHERE awaiting_paid_proof = true
          AND awaiting_paid_proof_at IS NOT NULL
          AND awaiting_paid_proof_at < %s
        ORDER BY awaiting_paid_proof_at ASC
        LIMIT 100
        """,
        (cutoff,),
    )

    def iso(x):
        return x.isoformat() if x else None

    return {
        "ok": True,
        "cutoff_utc": cutoff.isoformat(),
        "origin_verificando_stuck": [
            {
                "public_id": r["public_id"],
                "origin_country": r["origin_country"],
                "dest_country": r["dest_country"],
                "status": r["status"],
                "created_at": iso(r["created_at"]),
                "updated_at": iso(r["updated_at"]),
            }
            for r in origin_rows
        ],
        "awaiting_paid_proof_stuck": [
            {
                "public_id": r["public_id"],
                "origin_country": r["origin_country"],
                "dest_country": r["dest_country"],
                "status": r["status"],
                "awaiting_paid_proof_at": iso(r["awaiting_paid_proof_at"]),
                "updated_at": iso(r["updated_at"]),
            }
            for r in pay_rows
        ],
    }
from datetime import date as _date

@app.get("/origin-wallets/daily")
def origin_wallets_daily(day: str = Query(..., description="YYYY-MM-DD (Venezuela)"), api_key: str = Depends(verify_api_key)):
    try:
        d = _date.fromisoformat(day)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid day format. Use YYYY-MM-DD")

    # Totales por país/moneda (lo que se aprobó/registró)
    totals = fetch_all(
        """
        SELECT origin_country, fiat_currency,
               COALESCE(SUM(amount_fiat),0) AS total_amount_fiat,
               COUNT(*) AS movements
        FROM origin_receipts_daily
        WHERE day=%s
        GROUP BY origin_country, fiat_currency
        ORDER BY origin_country, fiat_currency
        """,
        (d,),
    )

    totals_out = [
        {
            "origin_country": r["origin_country"],
            "fiat_currency": r["fiat_currency"],
            "total_amount_fiat": float(r["total_amount_fiat"]),
            "movements": int(r["movements"]),
        }
        for r in totals
    ]

    # Movimientos del día (audit)
    moves = fetch_all(
        """
        SELECT day, origin_country, fiat_currency, amount_fiat,
               ref_order_public_id,
               created_at, created_by_telegram_id, note,
               approved_at, approved_by_telegram_id, approved_note
        FROM origin_receipts_daily
        WHERE day=%s
        ORDER BY created_at ASC
        """,
        (d,),
    )

    def iso(x):
        return x.isoformat() if x else None

    moves_out = [
        {
            "day": str(r["day"]),
            "origin_country": r["origin_country"],
            "fiat_currency": r["fiat_currency"],
            "amount_fiat": float(r["amount_fiat"]) if r["amount_fiat"] is not None else None,
            "ref_order_public_id": r["ref_order_public_id"],
            "created_at": iso(r["created_at"]),
            "created_by_telegram_id": r["created_by_telegram_id"],
            "note": r["note"],
            "approved_at": iso(r["approved_at"]),
            "approved_by_telegram_id": r["approved_by_telegram_id"],
            "approved_note": r["approved_note"],
        }
        for r in moves
    ]

    return {"ok": True, "day": day, "totals": totals_out, "movements": moves_out}
@app.get("/origin-wallets/balance")
def origin_wallets_balance(day: str = Query(..., description="YYYY-MM-DD"), api_key: str = Depends(verify_api_key)):
    from datetime import date as _date
    try:
        d = _date.fromisoformat(day)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid day format. Use YYYY-MM-DD")

    rows = fetch_all(
        """
        WITH ins AS (
          SELECT origin_country, fiat_currency, COALESCE(SUM(amount_fiat),0) AS in_amount
          FROM origin_receipts_daily
          WHERE day=%s
          GROUP BY origin_country, fiat_currency
        ),
        outs AS (
          SELECT origin_country, fiat_currency, COALESCE(SUM(amount_fiat),0) AS out_amount
          FROM origin_sweeps
          WHERE day=%s
          GROUP BY origin_country, fiat_currency
        )
        SELECT
          COALESCE(ins.origin_country, outs.origin_country) AS origin_country,
          COALESCE(ins.fiat_currency, outs.fiat_currency) AS fiat_currency,
          COALESCE(ins.in_amount, 0) AS in_amount,
          COALESCE(outs.out_amount, 0) AS out_amount,
          COALESCE(ins.in_amount, 0) - COALESCE(outs.out_amount, 0) AS net_amount
        FROM ins
        FULL OUTER JOIN outs
          ON ins.origin_country=outs.origin_country AND ins.fiat_currency=outs.fiat_currency
        ORDER BY origin_country, fiat_currency
        """,
        (d, d),
    )

    out = []
    for r in rows:
        out.append(
            {
                "origin_country": r["origin_country"],
                "fiat_currency": r["fiat_currency"],
                "in_amount": float(r["in_amount"]),
                "out_amount": float(r["out_amount"]),
                "net_amount": float(r["net_amount"]),
            }
        )

    return {"ok": True, "day": day, "balances": out}
