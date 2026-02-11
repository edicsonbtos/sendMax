"""Router: Origin Wallets, Sweeps, Balances y Cierre diario"""

from datetime import date as _date, datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query, Header, HTTPException
from pydantic import BaseModel
from ..db import fetch_one, fetch_all
from ..auth import verify_api_key

router = APIRouter(tags=["origin_wallets"])

VET = timezone(timedelta(hours=-4))


class OriginSweepIn(BaseModel):
    day: str
    origin_country: str
    fiat_currency: str
    amount_fiat: float
    created_by_telegram_id: int | None = None
    note: str | None = None
    external_ref: str | None = None


class OriginCloseIn(BaseModel):
    day: str
    origin_country: str
    fiat_currency: str
    closed_by_telegram_id: int | None = None
    note: str | None = None


class OriginWithdrawIn(BaseModel):
    day: str
    origin_country: str
    fiat_currency: str
    amount_fiat: float
    created_by_telegram_id: int | None = None
    note: str | None = None
    external_ref: str | None = None


class OriginEmptyIn(BaseModel):
    day: str
    origin_country: str
    fiat_currency: str
    created_by_telegram_id: int | None = None
    note: str | None = None
    external_ref: str | None = None


def _parse_day(day: str) -> _date:
    try:
        return _date.fromisoformat(day)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid day format. Use YYYY-MM-DD")


def _iso(x):
    return x.isoformat() if x else None


def _calc_current_balance(d: _date, origin_country: str, fiat_currency: str) -> float:
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
        (prev, origin_country, fiat_currency, d, origin_country, fiat_currency, d, origin_country, fiat_currency),
    )
    return float(row["current_balance"] or 0) if row else 0.0


@router.get("/daily-close")
def daily_close(day: str = Query(...), api_key: str = Depends(verify_api_key)):
    d = _parse_day(day)
    start_local = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=VET)
    end_local = start_local + timedelta(days=1)
    start_utc = start_local.astimezone(timezone.utc)
    end_utc = end_local.astimezone(timezone.utc)

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

    row2 = fetch_one(
        """
        SELECT COALESCE(SUM(profit_usdt), 0) AS profit_usdt
        FROM orders
        WHERE status='PAGADA' AND paid_at >= %s AND paid_at < %s
        """,
        (start_utc, end_utc),
    )

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

    by_origin = [{"origin_country": r["origin_country"], "amount_origin_sum": float(r["total_amount_origin"])} for r in rows3]

    return {
        "ok": True,
        "day_local": day,
        "tz": "VET(UTC-4)",
        "window_utc": {"start": start_utc.isoformat(), "end": end_utc.isoformat()},
        "status_counts": dict(row) if row else {},
        "profit_usdt_paid_window": float(row2["profit_usdt"]) if row2 else 0.0,
        "volume_by_origin_amount_origin": by_origin,
    }


@router.get("/origin-wallets/daily")
def origin_wallets_daily(day: str = Query(...), api_key: str = Depends(verify_api_key)):
    d = _parse_day(day)

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

    return {
        "ok": True,
        "day": day,
        "totals": [
            {"origin_country": r["origin_country"], "fiat_currency": r["fiat_currency"],
             "total_amount_fiat": float(r["total_amount_fiat"]), "movements": int(r["movements"])}
            for r in totals
        ],
        "movements": [
            {"day": str(r["day"]), "origin_country": r["origin_country"], "fiat_currency": r["fiat_currency"],
             "amount_fiat": float(r["amount_fiat"]) if r["amount_fiat"] is not None else None,
             "ref_order_public_id": r["ref_order_public_id"],
             "created_at": _iso(r["created_at"]), "created_by_telegram_id": r["created_by_telegram_id"],
             "note": r["note"], "approved_at": _iso(r["approved_at"]),
             "approved_by_telegram_id": r["approved_by_telegram_id"], "approved_note": r["approved_note"]}
            for r in moves
        ],
    }


@router.get("/origin-wallets/balance")
def origin_wallets_balance(day: str = Query(...), api_key: str = Depends(verify_api_key)):
    d = _parse_day(day)
    rows = fetch_all(
        """
        WITH ins AS (
          SELECT origin_country, fiat_currency, COALESCE(SUM(amount_fiat),0) AS in_amount
          FROM origin_receipts_daily WHERE day=%s GROUP BY origin_country, fiat_currency
        ),
        outs AS (
          SELECT origin_country, fiat_currency, COALESCE(SUM(amount_fiat),0) AS out_amount
          FROM origin_sweeps WHERE day=%s GROUP BY origin_country, fiat_currency
        )
        SELECT COALESCE(ins.origin_country, outs.origin_country) AS origin_country,
          COALESCE(ins.fiat_currency, outs.fiat_currency) AS fiat_currency,
          COALESCE(ins.in_amount, 0) AS in_amount, COALESCE(outs.out_amount, 0) AS out_amount,
          COALESCE(ins.in_amount, 0) - COALESCE(outs.out_amount, 0) AS net_amount
        FROM ins FULL OUTER JOIN outs
          ON ins.origin_country=outs.origin_country AND ins.fiat_currency=outs.fiat_currency
        ORDER BY origin_country, fiat_currency
        """,
        (d, d),
    )
    return {
        "ok": True, "day": day,
        "balances": [{"origin_country": r["origin_country"], "fiat_currency": r["fiat_currency"],
                       "in_amount": float(r["in_amount"]), "out_amount": float(r["out_amount"]),
                       "net_amount": float(r["net_amount"])} for r in rows],
    }


@router.post("/origin-wallets/sweeps")
def create_origin_sweep(payload: OriginSweepIn, api_key: str = Depends(verify_api_key)):
    d = _parse_day(payload.day)
    row = fetch_one(
        """
        INSERT INTO origin_sweeps (day, origin_country, fiat_currency, amount_fiat, created_by_telegram_id, note, external_ref)
        VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id
        """,
        (d, payload.origin_country, payload.fiat_currency, payload.amount_fiat, payload.created_by_telegram_id, payload.note, payload.external_ref),
        rw=True,
    )
    return {"ok": True, "id": row["id"] if row else None}


@router.get("/origin-wallets/sweeps")
def list_origin_sweeps(day: str = Query(...), origin_country: str | None = Query(None), api_key: str = Depends(verify_api_key)):
    sql = """
        SELECT id, day, origin_country, fiat_currency, amount_fiat, created_at, created_by_telegram_id, note, external_ref
        FROM origin_sweeps WHERE day = %s
    """
    params = [day]
    if origin_country:
        sql += " AND origin_country = %s"
        params.append(origin_country)
    sql += " ORDER BY created_at DESC LIMIT 200"
    rows = fetch_all(sql, tuple(params))
    return {"ok": True, "day": day, "count": len(rows), "sweeps": rows}


@router.get("/origin-wallets/close-report")
def origin_wallets_close_report(day: str = Query(...), api_key: str = Depends(verify_api_key)):
    d = _parse_day(day)
    balances = fetch_all(
        """
        WITH ins AS (
          SELECT origin_country, fiat_currency, COALESCE(SUM(amount_fiat),0) AS in_amount
          FROM origin_receipts_daily WHERE day=%s GROUP BY origin_country, fiat_currency
        ),
        outs AS (
          SELECT origin_country, fiat_currency, COALESCE(SUM(amount_fiat),0) AS out_amount
          FROM origin_sweeps WHERE day=%s GROUP BY origin_country, fiat_currency
        )
        SELECT COALESCE(ins.origin_country, outs.origin_country) AS origin_country,
          COALESCE(ins.fiat_currency, outs.fiat_currency) AS fiat_currency,
          COALESCE(ins.in_amount, 0) AS in_amount, COALESCE(outs.out_amount, 0) AS out_amount,
          COALESCE(ins.in_amount, 0) - COALESCE(outs.out_amount, 0) AS net_amount
        FROM ins FULL OUTER JOIN outs
          ON ins.origin_country=outs.origin_country AND ins.fiat_currency=outs.fiat_currency
        ORDER BY origin_country, fiat_currency
        """,
        (d, d),
    )

    pending = fetch_all(
        """
        SELECT origin_country, COUNT(*) AS cnt FROM orders
        WHERE status='ORIGEN_VERIFICANDO'
          AND created_at >= (%s::date)::timestamptz AND created_at < ((%s::date)+interval '1 day')::timestamptz
        GROUP BY origin_country
        """,
        (d, d),
    )
    pending_map = {r["origin_country"]: int(r["cnt"]) for r in pending}

    closures = fetch_all("SELECT origin_country, fiat_currency, closed_at, closed_by_telegram_id, note, net_amount_at_close FROM origin_wallet_closures WHERE day=%s", (d,))
    close_map = {(r["origin_country"], r["fiat_currency"]): r for r in closures}

    out = []
    for r in balances:
        key = (r["origin_country"], r["fiat_currency"])
        closed = close_map.get(key)
        net = float(r["net_amount"])
        pend = pending_map.get(r["origin_country"], 0)
        out.append({
            "origin_country": r["origin_country"], "fiat_currency": r["fiat_currency"],
            "in_amount": float(r["in_amount"]), "out_amount": float(r["out_amount"]),
            "net_amount": net, "pending_origin_verificando_count": pend,
            "ok_to_close": (net == 0.0 and pend == 0), "closed": bool(closed),
            "closed_at": _iso(closed["closed_at"]) if closed else None,
            "closed_by_telegram_id": closed["closed_by_telegram_id"] if closed else None,
            "close_note": closed["note"] if closed else None,
            "net_amount_at_close": float(closed["net_amount_at_close"]) if closed else None,
        })
    return {"ok": True, "day": day, "items": out}


@router.post("/origin-wallets/close")
def origin_wallets_close(payload: OriginCloseIn, api_key: str = Depends(verify_api_key)):
    d = _parse_day(payload.day)
    net_row = fetch_one(
        """
        WITH ins AS (SELECT COALESCE(SUM(amount_fiat),0) AS in_amount FROM origin_receipts_daily WHERE day=%s AND origin_country=%s AND fiat_currency=%s),
        outs AS (SELECT COALESCE(SUM(amount_fiat),0) AS out_amount FROM origin_sweeps WHERE day=%s AND origin_country=%s AND fiat_currency=%s)
        SELECT (SELECT in_amount FROM ins) - (SELECT out_amount FROM outs) AS net_amount
        """,
        (d, payload.origin_country, payload.fiat_currency, d, payload.origin_country, payload.fiat_currency),
    )
    net_amount = float(net_row["net_amount"]) if net_row and net_row["net_amount"] is not None else 0.0

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
        row = fetch_one("SELECT id FROM origin_wallet_closures WHERE day=%s AND origin_country=%s AND fiat_currency=%s", (d, payload.origin_country, payload.fiat_currency))
    return {"ok": True, "id": row["id"] if row else None, "net_amount_at_close": net_amount}


@router.post("/origin-wallets/withdraw")
def origin_wallets_withdraw(payload: OriginWithdrawIn, api_key: str = Depends(verify_api_key)):
    d = _parse_day(payload.day)
    if payload.amount_fiat <= 0:
        raise HTTPException(status_code=400, detail="amount_fiat must be > 0")
    current_balance = _calc_current_balance(d, payload.origin_country, payload.fiat_currency)
    if payload.amount_fiat > current_balance:
        raise HTTPException(status_code=400, detail=f"Insufficient funds. current_balance={current_balance}")
    ins_row = fetch_one(
        """
        INSERT INTO origin_sweeps (day, origin_country, fiat_currency, amount_fiat, created_by_telegram_id, note, external_ref)
        VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id
        """,
        (d, payload.origin_country, payload.fiat_currency, payload.amount_fiat, payload.created_by_telegram_id, payload.note, payload.external_ref),
        rw=True,
    )
    return {"ok": True, "id": ins_row["id"] if ins_row else None, "withdrawn": payload.amount_fiat, "current_balance_before": current_balance}


@router.post("/origin-wallets/empty")
def origin_wallets_empty(payload: OriginEmptyIn, api_key: str = Depends(verify_api_key)):
    d = _parse_day(payload.day)
    current_balance = _calc_current_balance(d, payload.origin_country, payload.fiat_currency)
    if current_balance <= 0:
        return {"ok": True, "emptied": 0.0, "message": "Already empty"}
    ins_row = fetch_one(
        """
        INSERT INTO origin_sweeps (day, origin_country, fiat_currency, amount_fiat, created_by_telegram_id, note, external_ref)
        VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id
        """,
        (d, payload.origin_country, payload.fiat_currency, current_balance, payload.created_by_telegram_id, payload.note, payload.external_ref),
        rw=True,
    )
    return {"ok": True, "id": ins_row["id"] if ins_row else None, "emptied": current_balance}


@router.get("/origin-wallets/current-balances")
def origin_wallets_current_balances(api_key: str = Depends(verify_api_key)):
    rows = fetch_all(
        """
        WITH ins AS (
          SELECT origin_country, fiat_currency, COALESCE(SUM(amount_fiat),0) AS total_in
          FROM origin_receipts_daily GROUP BY origin_country, fiat_currency
        ),
        outs AS (
          SELECT origin_country, fiat_currency, COALESCE(SUM(amount_fiat),0) AS total_out
          FROM origin_sweeps GROUP BY origin_country, fiat_currency
        )
        SELECT COALESCE(ins.origin_country, outs.origin_country) AS origin_country,
          COALESCE(ins.fiat_currency, outs.fiat_currency) AS fiat_currency,
          COALESCE(ins.total_in, 0) AS total_in, COALESCE(outs.total_out, 0) AS total_out,
          COALESCE(ins.total_in, 0) - COALESCE(outs.total_out, 0) AS current_balance
        FROM ins FULL OUTER JOIN outs
          ON ins.origin_country=outs.origin_country AND ins.fiat_currency=outs.fiat_currency
        ORDER BY origin_country, fiat_currency
        """
    )
    return {
        "ok": True,
        "items": [{"origin_country": r["origin_country"], "fiat_currency": r["fiat_currency"],
                    "total_in": float(r["total_in"] or 0), "total_out": float(r["total_out"] or 0),
                    "current_balance": float(r["current_balance"] or 0)} for r in rows],
    }


@router.get("/origin-wallets/balances2")
def origin_wallets_balances2(day: str = Query(...), api_key: str = Depends(verify_api_key)):
    d = _parse_day(day)
    prev = d - timedelta(days=1)
    rows = fetch_all(
        """
        WITH opening AS (
          SELECT origin_country, fiat_currency, COALESCE(net_amount_at_close, 0) AS opening_balance
          FROM origin_wallet_closures WHERE day=%s
        ),
        ins AS (
          SELECT origin_country, fiat_currency, COALESCE(SUM(amount_fiat),0) AS in_today
          FROM origin_receipts_daily WHERE day=%s GROUP BY origin_country, fiat_currency
        ),
        outs AS (
          SELECT origin_country, fiat_currency, COALESCE(SUM(amount_fiat),0) AS out_today
          FROM origin_sweeps WHERE day=%s GROUP BY origin_country, fiat_currency
        ),
        keys AS (
          SELECT origin_country, fiat_currency FROM opening
          UNION SELECT origin_country, fiat_currency FROM ins
          UNION SELECT origin_country, fiat_currency FROM outs
        )
        SELECT k.origin_country, k.fiat_currency,
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
    return {
        "ok": True, "day": day, "prev_day": str(prev),
        "items": [{"origin_country": r["origin_country"], "fiat_currency": r["fiat_currency"],
                    "opening_balance": float(r["opening_balance"] or 0), "in_today": float(r["in_today"] or 0),
                    "out_today": float(r["out_today"] or 0), "current_balance": float(r["current_balance"] or 0)} for r in rows],
    }
