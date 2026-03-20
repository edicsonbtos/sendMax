from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import csv
import io
import json
from fastapi.responses import StreamingResponse
from typing import List, Optional

from ..auth import require_admin
from ..db import fetch_one, fetch_all, run_in_transaction
from ..schemas.daily_closure import DailyClosureExecuteRequest, DailyClosureResponse, ClosureMetrics, ClosureWarning

router = APIRouter(prefix="/daily_closure", tags=["daily-close"])

VET = timezone(timedelta(hours=-4))

async def _parse_date_range(d: date):
    # Start of day in local time (VET)
    start_local = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=VET)
    end_local = start_local + timedelta(days=1)
    # Convert to UTC for DB queries
    start_utc = start_local.astimezone(timezone.utc)
    end_utc = end_local.astimezone(timezone.utc)
    return start_utc, end_utc

@router.post("/execute", response_model=DailyClosureResponse)
async def execute_daily_closure(
    payload: DailyClosureExecuteRequest,
    auth: dict = Depends(require_admin)
):
    d = payload.closure_date
    start_utc, end_utc = await _parse_date_range(d)

    # 1. Check if already exists
    existing = await fetch_one("SELECT id FROM daily_closures WHERE closure_date = %s", (d,))
    if existing and not payload.force:
        raise HTTPException(status_code=409, detail=f"Cierre para el día {d} ya existe. Use 'force' para sobrescribir.")

    # 2. Gather Metrics
    # Orders metrics: Completadas vs Canceladas
    counts = await fetch_one(
        """
        SELECT 
            COUNT(*) FILTER (WHERE status IN ('PAGADA', 'COMPLETADA')) as completed_count,
            COUNT(*) FILTER (WHERE status = 'CANCELADA') as cancelled_count,
            COALESCE(SUM(amount_origin) FILTER (WHERE status IN ('PAGADA', 'COMPLETADA')), 0) as total_volume,
            COALESCE(SUM(profit_usdt) FILTER (WHERE status IN ('PAGADA', 'COMPLETADA')), 0) as total_profit,
            COALESCE(SUM(profit_real_usdt) FILTER (WHERE status IN ('PAGADA', 'COMPLETADA')), 0) as total_profit_real
        FROM orders 
        WHERE (paid_at >= %s AND paid_at < %s) OR (status = 'CANCELADA' AND updated_at >= %s AND updated_at < %s)
        """,
        (start_utc, end_utc, start_utc, end_utc)
    )

    total_orders = counts['completed_count'] + counts['cancelled_count']
    success_rate = (counts['completed_count'] / total_orders * 100) if total_orders > 0 else 100

    # Best Operator
    best_op = await fetch_one(
        """
        SELECT u.id, u.alias, COUNT(o.id) as order_count
        FROM orders o
        JOIN users u ON o.operator_user_id = u.id
        WHERE o.status IN ('PAGADA', 'COMPLETADA') AND o.paid_at >= %s AND o.paid_at < %s
        GROUP BY u.id, u.alias
        ORDER BY order_count DESC
        LIMIT 1
        """,
        (start_utc, end_utc)
    )

    # Best Countries
    best_origin = await fetch_one(
        "SELECT origin_country, COUNT(*) as cnt FROM orders WHERE status IN ('PAGADA', 'COMPLETADA') AND paid_at >= %s AND paid_at < %s GROUP BY origin_country ORDER BY cnt DESC LIMIT 1",
        (start_utc, end_utc)
    )
    best_dest = await fetch_one(
        "SELECT dest_country, COUNT(*) as cnt FROM orders WHERE status IN ('PAGADA', 'COMPLETADA') AND paid_at >= %s AND paid_at < %s GROUP BY dest_country ORDER BY cnt DESC LIMIT 1",
        (start_utc, end_utc)
    )

    # Withdrawals
    withdrawals = await fetch_one(
        "SELECT COUNT(*) as cnt, COALESCE(SUM(amount_usdt), 0) as total FROM withdrawals WHERE status = 'SOLICITADA'"
    )

    # Snapshots
    vaults = await fetch_all("SELECT name, vault_type, balance, currency FROM vaults WHERE is_active = true")
    wallets = await fetch_all(
        """
        SELECT u.alias, w.balance_usdt 
        FROM wallets w 
        JOIN users u ON w.user_id = u.id 
        WHERE w.balance_usdt > 0
        """
    )

    def _json_dumps(data):
        return json.dumps(data, default=str)

    # Build record with json-serialized snapshots
    vaults_json = _json_dumps(vaults)
    wallets_json = _json_dumps(wallets)

    async def _create_record(cur):
        if existing:
            await cur.execute("DELETE FROM daily_closures WHERE closure_date = %s", (d,))
        
        await cur.execute(
            """
            INSERT INTO daily_closures (
                closure_date, total_orders_count, total_volume_origin, 
                total_profit_usdt, total_profit_real, success_rate,
                best_operator_id, best_operator_alias,
                best_origin_country, best_dest_country,
                pending_withdrawals_count, pending_withdrawals_amount,
                vaults_snapshot, wallet_balances_snapshot,
                notes, executed_by
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                d, total_orders, counts['total_volume'],
                counts['total_profit'], counts['total_profit_real'], success_rate,
                best_op['id'] if best_op else None, best_op['alias'] if best_op else None,
                best_origin['origin_country'] if best_origin else None, best_dest['dest_country'] if best_dest else None,
                withdrawals['cnt'], withdrawals['total'],
                vaults_json, wallets_json,
                payload.notes, auth['user_id']
            )
        )
        return await cur.fetchone()

    new_record = await run_in_transaction(_create_record)
    return new_record

@router.post("/close")
async def close_day_alias(
    payload: DailyClosureExecuteRequest,
    auth: dict = Depends(require_admin)
):
    """Alias para execute_daily_closure usado por el frontend."""
    return await execute_daily_closure(payload, auth)

@router.get("/report")
async def get_daily_report(day: str = Query(...), auth: dict = Depends(require_admin)):
    """Genera el reporte de entradas/salidas por pais."""
    try:
        d = date.fromisoformat(day)
    except:
        raise HTTPException(status_code=400, detail="Formato de fecha invalido (YYYY-MM-DD)")
    
    start_utc, end_utc = await _parse_date_range(d)
    
    rows = await fetch_all("""
        SELECT 
            origin_country as country,
            'USDT' as currency,
            COALESCE(SUM(amount_origin), 0) as total_in,
            COALESCE(SUM(amount_origin - profit_real_usdt), 0) as total_out,
            COALESCE(SUM(profit_real_usdt), 0) as net_balance
        FROM orders
        WHERE status IN ('PAGADA', 'COMPLETADA') 
          AND paid_at >= %s AND paid_at < %s
        GROUP BY origin_country
    """, (start_utc, end_utc))
    
    result = []
    for r in rows:
        result.append({
            "country": r["country"],
            "currency": r["currency"],
            "total_in": float(r["total_in"]),
            "total_out": float(r["total_out"]),
            "net_balance": float(r["net_balance"])
        })
    return result

@router.get("/history", response_model=List[DailyClosureResponse])
async def get_closure_history(
    limit: int = Query(30, ge=1, le=100),
    auth: dict = Depends(require_admin)
):
    rows = await fetch_all("SELECT * FROM daily_closures ORDER BY closure_date DESC LIMIT %s", (limit,))
    return rows

@router.get("/{closure_date}", response_model=DailyClosureResponse)
async def get_closure_details(
    closure_date: date,
    auth: dict = Depends(require_admin)
):
    row = await fetch_one("SELECT * FROM daily_closures WHERE closure_date = %s", (closure_date,))
    if not row:
        raise HTTPException(status_code=404, detail="Cierre no encontrado")
    return row

@router.post("/{closure_date}/export-csv")
async def export_closure_csv(
    closure_date: date,
    auth: dict = Depends(require_admin)
):
    row = await fetch_one("SELECT * FROM daily_closures WHERE closure_date = %s", (closure_date,))
    if not row:
        raise HTTPException(status_code=404, detail="Cierre no encontrado")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Métrica", "Valor"])
    writer.writerow(["Fecha Cierre", str(row['closure_date'])])
    writer.writerow(["Órdenes Totales", row['total_orders_count']])
    writer.writerow(["Volumen Origen", row['total_volume_origin']])
    writer.writerow(["Profit Real USDT", row['total_profit_real']])
    writer.writerow(["Success Rate", f"{row['success_rate']}%"])
    writer.writerow(["Mejor Operador", row['best_operator_alias']])
    writer.writerow(["Retiros Pendientes", row['pending_withdrawals_count']])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=cierre_{closure_date}.csv"}
    )
