from fastapi import FastAPI, Header, Query, Request, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
import os
import json
from .db import fetch_one, fetch_all

app = FastAPI(title="Sendmax Backoffice API", version="0.5.2")

# Configuración de API Key
API_KEY = os.getenv("BACKOFFICE_API_KEY")
if not API_KEY:
    raise RuntimeError("BACKOFFICE_API_KEY no está configurada en este servicio")
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
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://sendmax-bot.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
          COUNT(*) FILTER (WHERE awaiting_paid_proof=true) AS awaiting_paid_proof,

          -- Profit: sumamos profit_usdt solo de PAGADA (orden completada)
          COALESCE(SUM(profit_usdt) FILTER (WHERE status='PAGADA'), 0) AS total_profit_usd,

          -- Volumen: SOLO es correcto si amount_origin ya esta en USD.
          -- Si NO esta en USD, dejalo en 0 y luego definimos la regla.
          0::numeric AS total_volume_usd
        FROM orders
        """
    )

    creadas = int(row["creadas"] or 0)
    en_proceso = int(row["en_proceso"] or 0)
    pagadas = int(row["pagadas"] or 0)
    canceladas = int(row["canceladas"] or 0)

    total_orders = creadas + en_proceso + pagadas + canceladas
    pending_orders = creadas + en_proceso
    completed_orders = pagadas

    return {
        # Contrato esperado por el frontend (Overview)
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "completed_orders": completed_orders,
        "total_volume_usd": float(row["total_volume_usd"] or 0),
        "total_profit_usd": float(row["total_profit_usd"] or 0),

        # Extras (no rompen el frontend; utiles para otras vistas)
        "status_counts": {
            "CREADA": creadas,
            "EN_PROCESO": en_proceso,
            "PAGADA": pagadas,
            "CANCELADA": canceladas,
        },
        "awaiting_paid_proof": int(row["awaiting_paid_proof"] or 0),
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
from pydantic import BaseModel
from typing import Any, Dict

class OriginSweepIn(BaseModel):
    day: str  # YYYY-MM-DD
    origin_country: str
    fiat_currency: str
    amount_fiat: float
    created_by_telegram_id: int | None = None
    note: str | None = None
    external_ref: str | None = None

@app.post("/origin-wallets/sweeps")
def create_origin_sweep(payload: OriginSweepIn, api_key: str = Depends(verify_api_key)):
    from datetime import date as _date
    try:
        d = _date.fromisoformat(payload.day)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid day format. Use YYYY-MM-DD")

    # Insert
    row = fetch_one(
        """
        INSERT INTO origin_sweeps (day, origin_country, fiat_currency, amount_fiat, created_by_telegram_id, note, external_ref)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        RETURNING id
        """,
        (d, payload.origin_country, payload.fiat_currency, payload.amount_fiat, payload.created_by_telegram_id, payload.note, payload.external_ref),
        rw=True,
    )

    return {"ok": True, "id": row["id"] if row else None}
@app.get("/diag/env")
def diag_env(api_key: str = Depends(verify_api_key)):
    import os
    return {
        "ok": True,
        "has_DATABASE_URL_RO": bool(os.getenv("DATABASE_URL_RO")),
        "has_DATABASE_URL_RW": bool(os.getenv("DATABASE_URL_RW")),
        "has_BACKOFFICE_API_KEY": bool(os.getenv("BACKOFFICE_API_KEY")),
    }
@app.get("/diag/db-users")
def diag_db_users(api_key: str = Depends(verify_api_key)):
    # current_user en RO y RW, sin revelar URLs
    ro = fetch_one("SELECT current_user AS u", ())
    rw = fetch_one("SELECT current_user AS u", (), rw=True)
    return {"ok": True, "ro_user": ro["u"] if ro else None, "rw_user": rw["u"] if rw else None}
# --- TEMP: safe error wrapper for sweeps POST ---
from psycopg import Error as PsycopgError

_old_create_origin_sweep = create_origin_sweep

@app.post("/origin-wallets/sweeps_debug")
def create_origin_sweep_debug(payload: OriginSweepIn, api_key: str = Depends(verify_api_key)):
    try:
        return _old_create_origin_sweep(payload, api_key)
    except PsycopgError as e:
        return {"ok": False, "db_error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}
class OriginCloseIn(BaseModel):
    day: str
    origin_country: str
    fiat_currency: str
    closed_by_telegram_id: int | None = None
    note: str | None = None

@app.get("/origin-wallets/close-report")
def origin_wallets_close_report(day: str = Query(...), api_key: str = Depends(verify_api_key)):
    from datetime import date as _date
    try:
        d = _date.fromisoformat(day)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid day format. Use YYYY-MM-DD")

    # balances (in/out/net)
    balances = fetch_all(
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

    # pendientes ORIGEN_VERIFICANDO del día por país
    pending = fetch_all(
        """
        SELECT origin_country, COUNT(*) AS cnt
        FROM orders
        WHERE status='ORIGEN_VERIFICANDO'
          AND created_at >= (%s::date)::timestamptz
          AND created_at < ((%s::date)+interval '1 day')::timestamptz
        GROUP BY origin_country
        """,
        (d, d),
    )
    pending_map = {r["origin_country"]: int(r["cnt"]) for r in pending}

    # cierres existentes
    closures = fetch_all(
        """
        SELECT origin_country, fiat_currency, closed_at, closed_by_telegram_id, note, net_amount_at_close
        FROM origin_wallet_closures
        WHERE day=%s
        """,
        (d,),
    )
    close_map = {(r["origin_country"], r["fiat_currency"]): r for r in closures}

    def iso(x): return x.isoformat() if x else None

    out = []
    for r in balances:
        key = (r["origin_country"], r["fiat_currency"])
        closed = close_map.get(key)
        net = float(r["net_amount"])
        pend = pending_map.get(r["origin_country"], 0)
        out.append({
            "origin_country": r["origin_country"],
            "fiat_currency": r["fiat_currency"],
            "in_amount": float(r["in_amount"]),
            "out_amount": float(r["out_amount"]),
            "net_amount": net,
            "pending_origin_verificando_count": pend,
            "ok_to_close": (net == 0.0 and pend == 0),
            "closed": bool(closed),
            "closed_at": iso(closed["closed_at"]) if closed else None,
            "closed_by_telegram_id": closed["closed_by_telegram_id"] if closed else None,
            "close_note": closed["note"] if closed else None,
            "net_amount_at_close": float(closed["net_amount_at_close"]) if closed else None,
        })

    return {"ok": True, "day": day, "items": out}

@app.post("/origin-wallets/close")
def origin_wallets_close(payload: OriginCloseIn, api_key: str = Depends(verify_api_key)):
    from datetime import date as _date
    try:
        d = _date.fromisoformat(payload.day)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid day format. Use YYYY-MM-DD")

    # calcular net actual
    net_row = fetch_one(
        """
        WITH ins AS (
          SELECT COALESCE(SUM(amount_fiat),0) AS in_amount
          FROM origin_receipts_daily
          WHERE day=%s AND origin_country=%s AND fiat_currency=%s
        ),
        outs AS (
          SELECT COALESCE(SUM(amount_fiat),0) AS out_amount
          FROM origin_sweeps
          WHERE day=%s AND origin_country=%s AND fiat_currency=%s
        )
        SELECT (SELECT in_amount FROM ins) - (SELECT out_amount FROM outs) AS net_amount
        """,
        (d, payload.origin_country, payload.fiat_currency, d, payload.origin_country, payload.fiat_currency),
    )
    net_amount = float(net_row["net_amount"]) if net_row and net_row["net_amount"] is not None else 0.0

    # insertar cierre (RW)
    row = fetch_one(
        """
        INSERT INTO origin_wallet_closures (day, origin_country, fiat_currency, closed_by_telegram_id, note, net_amount_at_close)
        VALUES (%s,%s,%s,%s,%s,%s)
        ON CONFLICT (day, origin_country, fiat_currency) DO NOTHING
        RETURNING id
        """,
        (d, payload.origin_country, payload.fiat_currency, payload.closed_by_telegram_id, payload.note, net_amount),
        rw=True,
    )
    if not row:
        row = fetch_one(
            "SELECT id FROM origin_wallet_closures WHERE day=%s AND origin_country=%s AND fiat_currency=%s",
            (d, payload.origin_country, payload.fiat_currency),
            rw=False,
        )
    return {"ok": True, "id": row["id"] if row else None, "net_amount_at_close": net_amount, "already_closed": True if row else False}
@app.get("/version2")
def version2():
    return {"ok": True, "marker": "deployed_after_close_endpoints", "ts": "2026-02-06"}

# ---- Added: GET /origin-wallets/sweeps (list) ----

@app.get("/origin-wallets/sweeps")
def list_origin_sweeps(
    day: str = Query(..., description="YYYY-MM-DD"),
    origin_country: str | None = Query(None),
    x_api_key: str = Header(..., alias="X-API-KEY"),
):
    verify_api_key(x_api_key)

    sql = """
        SELECT
            id,
            day,
            origin_country,
            fiat_currency,
            amount_fiat,
            created_at,
            created_by_telegram_id,
            note,
            external_ref
        FROM origin_sweeps
        WHERE day = %s
    """
    params: list = [day]

    if origin_country:
        sql += " AND origin_country = %s"
        params.append(origin_country)

    sql += " ORDER BY created_at DESC LIMIT 200"

    rows = fetch_all(sql, tuple(params))
    return {"ok": True, "day": day, "count": len(rows), "sweeps": rows}
# ---- End added ----

@app.get("/gitsha")
def gitsha():
    import os
    return {
        "ok": True,
        "railway_commit": os.getenv("RAILWAY_GIT_COMMIT_SHA") or os.getenv("RAILWAY_GIT_COMMIT") or "unknown",
    }









### ADMIN_SETTINGS_ENDPOINTS
class SettingsUpdate(BaseModel):
    value_json: Dict[str, Any]

@app.get("/admin/settings")
def get_admin_settings(api_key: str = Depends(verify_api_key)):
    rows = fetch_all("SELECT key, value_json, updated_at, updated_by FROM settings ORDER BY key")
    return {"items": rows}

@app.put("/admin/settings/{key}")
def put_admin_settings(
    key: str,
    payload: SettingsUpdate,
    request: Request,
    api_key: str = Depends(verify_api_key),
):
    before = fetch_one("SELECT key, value_json FROM settings WHERE key=%s", (key,))
    before_json = before["value_json"] if before else None

    # upsert settings (RW)
    fetch_one(
        """
        INSERT INTO settings(key, value_json, updated_at, updated_by)
        VALUES (%s, %s::jsonb, now(), NULL)
        ON CONFLICT (key) DO UPDATE
          SET value_json=EXCLUDED.value_json,
              updated_at=now(),
              updated_by=NULL
        RETURNING key
        """,
        (key, json.dumps(payload.value_json)),
        rw=True,
    )

    after = fetch_one("SELECT key, value_json FROM settings WHERE key=%s", (key,))
    after_json = after["value_json"] if after else None

    # audit (RW)
    fetch_one(
        """
        INSERT INTO audit_log(actor_user_id, action, entity_type, entity_id, before_json, after_json, ip, user_agent)
        VALUES (NULL, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s)
        RETURNING id
        """,
        (
            "SETTINGS_UPDATED",
            "settings",
            key,
            json.dumps(before_json) if before_json is not None else None,
            json.dumps(after_json) if after_json is not None else None,
            request.client.host if request.client else None,
            request.headers.get("user-agent"),
        ),
        rw=True,
    )

    return {"ok": True, "key": key, "value_json": after_json}

@app.get("/diag/db-roles")
def diag_db_roles(api_key: str = Depends(verify_api_key)):
    ro = fetch_one("SELECT current_user AS u", (), rw=False)
    rw = fetch_one("SELECT current_user AS u", (), rw=True)
    return {"ro_user": ro["u"] if ro else None, "rw_user": rw["u"] if rw else None}



@app.get("/origin-wallets/balances2")
def origin_wallets_balances2(
    day: str = Query(..., description="YYYY-MM-DD"),
    api_key: str = Depends(verify_api_key),
):
    from datetime import date as _date, timedelta
    try:
        d = _date.fromisoformat(day)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid day format. Use YYYY-MM-DD")

    prev = d - timedelta(days=1)

    rows = fetch_all(
        """
        WITH opening AS (
          SELECT origin_country, fiat_currency, COALESCE(net_amount_at_close, 0) AS opening_balance
          FROM origin_wallet_closures
          WHERE day=%s
        ),
        ins AS (
          SELECT origin_country, fiat_currency, COALESCE(SUM(amount_fiat),0) AS in_today
          FROM origin_receipts_daily
          WHERE day=%s
          GROUP BY origin_country, fiat_currency
        ),
        outs AS (
          SELECT origin_country, fiat_currency, COALESCE(SUM(amount_fiat),0) AS out_today
          FROM origin_sweeps
          WHERE day=%s
          GROUP BY origin_country, fiat_currency
        ),
        keys AS (
          SELECT origin_country, fiat_currency FROM opening
          UNION SELECT origin_country, fiat_currency FROM ins
          UNION SELECT origin_country, fiat_currency FROM outs
        )
        SELECT
          k.origin_country,
          k.fiat_currency,
          COALESCE(o.opening_balance, 0) AS opening_balance,
          COALESCE(i.in_today, 0) AS in_today,
          COALESCE(o2.out_today, 0) AS out_today,
          COALESCE(o.opening_balance, 0) + COALESCE(i.in_today, 0) - COALESCE(o2.out_today, 0) AS current_balance
        FROM keys k
        LEFT JOIN opening o ON o.origin_country=k.origin_country AND o.fiat_currency=k.fiat_currency
        LEFT JOIN ins i ON i.origin_country=k.origin_country AND i.fiat_currency=k.fiat_currency
        LEFT JOIN outs o2 ON o2.origin_country=k.origin_country AND o2.fiat_currency=k.fiat_currency
        ORDER BY k.origin_country, k.fiat_currency
        """,
        (prev, d, d),
    )

    items = []
    for r in rows:
        items.append({
            "origin_country": r["origin_country"],
            "fiat_currency": r["fiat_currency"],
            "opening_balance": float(r["opening_balance"] or 0),
            "in_today": float(r["in_today"] or 0),
            "out_today": float(r["out_today"] or 0),
            "current_balance": float(r["current_balance"] or 0),
        })

    return {"ok": True, "day": day, "prev_day": str(prev), "items": items}

class OriginWithdrawIn(BaseModel):
    day: str
    origin_country: str
    fiat_currency: str
    amount_fiat: float
    created_by_telegram_id: int | None = None
    note: str | None = None
    external_ref: str | None = None

@app.post("/origin-wallets/withdraw")
def origin_wallets_withdraw(payload: OriginWithdrawIn, api_key: str = Depends(verify_api_key)):
    from datetime import date as _date, timedelta
    try:
        d = _date.fromisoformat(payload.day)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid day format. Use YYYY-MM-DD")

    if payload.amount_fiat <= 0:
        raise HTTPException(status_code=400, detail="amount_fiat must be > 0")

    # calcular saldo actual (opening + in_today - out_today)
    prev = d - timedelta(days=1)
    row = fetch_one(
        """
        WITH opening AS (
          SELECT COALESCE(net_amount_at_close, 0) AS opening_balance
          FROM origin_wallet_closures
          WHERE day=%s AND origin_country=%s AND fiat_currency=%s
        ),
        ins AS (
          SELECT COALESCE(SUM(amount_fiat),0) AS in_today
          FROM origin_receipts_daily
          WHERE day=%s AND origin_country=%s AND fiat_currency=%s
        ),
        outs AS (
          SELECT COALESCE(SUM(amount_fiat),0) AS out_today
          FROM origin_sweeps
          WHERE day=%s AND origin_country=%s AND fiat_currency=%s
        )
        SELECT
          COALESCE((SELECT opening_balance FROM opening), 0)
          + COALESCE((SELECT in_today FROM ins), 0)
          - COALESCE((SELECT out_today FROM outs), 0) AS current_balance
        """,
        (prev, payload.origin_country, payload.fiat_currency, d, payload.origin_country, payload.fiat_currency, d, payload.origin_country, payload.fiat_currency),
    )
    current_balance = float(row["current_balance"] or 0) if row else 0.0

    if payload.amount_fiat > current_balance:
        raise HTTPException(status_code=400, detail=f"Insufficient funds. current_balance={current_balance}")

    # crear sweep (RW)
    ins_row = fetch_one(
        """
        INSERT INTO origin_sweeps (day, origin_country, fiat_currency, amount_fiat, created_by_telegram_id, note, external_ref)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        RETURNING id
        """,
        (d, payload.origin_country, payload.fiat_currency, payload.amount_fiat, payload.created_by_telegram_id, payload.note, payload.external_ref),
        rw=True,
    )

    return {"ok": True, "id": ins_row["id"] if ins_row else None, "withdrawn": payload.amount_fiat, "current_balance_before": current_balance}

class OriginEmptyIn(BaseModel):
    day: str
    origin_country: str
    fiat_currency: str
    created_by_telegram_id: int | None = None
    note: str | None = None
    external_ref: str | None = None

@app.post("/origin-wallets/empty")
def origin_wallets_empty(payload: OriginEmptyIn, api_key: str = Depends(verify_api_key)):
    from datetime import date as _date, timedelta
    try:
        d = _date.fromisoformat(payload.day)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid day format. Use YYYY-MM-DD")

    prev = d - timedelta(days=1)
    row = fetch_one(
        """
        WITH opening AS (
          SELECT COALESCE(net_amount_at_close, 0) AS opening_balance
          FROM origin_wallet_closures
          WHERE day=%s AND origin_country=%s AND fiat_currency=%s
        ),
        ins AS (
          SELECT COALESCE(SUM(amount_fiat),0) AS in_today
          FROM origin_receipts_daily
          WHERE day=%s AND origin_country=%s AND fiat_currency=%s
        ),
        outs AS (
          SELECT COALESCE(SUM(amount_fiat),0) AS out_today
          FROM origin_sweeps
          WHERE day=%s AND origin_country=%s AND fiat_currency=%s
        )
        SELECT
          COALESCE((SELECT opening_balance FROM opening), 0)
          + COALESCE((SELECT in_today FROM ins), 0)
          - COALESCE((SELECT out_today FROM outs), 0) AS current_balance
        """,
        (prev, payload.origin_country, payload.fiat_currency, d, payload.origin_country, payload.fiat_currency, d, payload.origin_country, payload.fiat_currency),
    )
    current_balance = float(row["current_balance"] or 0) if row else 0.0

    if current_balance <= 0:
        return {"ok": True, "emptied": 0.0, "message": "Already empty"}

    ins_row = fetch_one(
        """
        INSERT INTO origin_sweeps (day, origin_country, fiat_currency, amount_fiat, created_by_telegram_id, note, external_ref)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        RETURNING id
        """,
        (d, payload.origin_country, payload.fiat_currency, current_balance, payload.created_by_telegram_id, payload.note, payload.external_ref),
        rw=True,
    )

    return {"ok": True, "id": ins_row["id"] if ins_row else None, "emptied": current_balance}

@app.get("/origin-wallets/current-balances")
def origin_wallets_current_balances(api_key: str = Depends(verify_api_key)):
    rows = fetch_all(
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
          COALESCE(ins.total_in, 0) AS total_in,
          COALESCE(outs.total_out, 0) AS total_out,
          COALESCE(ins.total_in, 0) - COALESCE(outs.total_out, 0) AS current_balance
        FROM ins
        FULL OUTER JOIN outs
          ON ins.origin_country=outs.origin_country AND ins.fiat_currency=outs.fiat_currency
        ORDER BY origin_country, fiat_currency
        """
    )

    items = []
    for r in rows:
        items.append({
            "origin_country": r["origin_country"],
            "fiat_currency": r["fiat_currency"],
            "total_in": float(r["total_in"] or 0),
            "total_out": float(r["total_out"] or 0),
            "current_balance": float(r["current_balance"] or 0),
        })

    return {"ok": True, "items": items}
