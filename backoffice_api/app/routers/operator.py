"""
Router: Dashboard del Operador autenticado (JWT).
GET /operator/me/dashboard — require_operator_or_admin
Devuelve datos exclusivos del operador cuyo user_id está en el JWT.
"""
from __future__ import annotations
import logging
from fastapi import APIRouter, Depends, HTTPException
from decimal import Decimal
from ..auth import require_operator_or_admin
from ..db import fetch_one, fetch_all
from ..services.financial_reads import (
    get_user_profit_metrics,
    get_user_ledger,
    get_user_withdrawals,
    get_operator_leaderboard,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/operator", tags=["Operator"])

# ——————————————————————————————————————————
# Helpers de serialización
# ——————————————————————————————————————————

def _s(v):
    """Serializa Decimal, datetime y None para JSON."""
    if v is None:
        return None
    if isinstance(v, Decimal):
        return str(v.quantize(Decimal("0.01")))
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return v

def _row(row: dict | None) -> dict | None:
    if not row:
        return None
    return {k: _s(v) for k, v in row.items()}

def _rows(rows) -> list[dict]:
    return [_row(r) for r in (rows or [])]  # type: ignore[misc]


# ——————————————————————————————————————————
# GET /operator/me/dashboard
# ——————————————————————————————————————————

@router.get("/me/dashboard")
async def get_operator_dashboard(auth: dict = Depends(require_operator_or_admin)):
    """
    Dashboard personal del operador autenticado.
    Los datos siempre son filtrados por user_id del JWT (cada operador ve solo los suyos).
    """
    user_id = auth.get("user_id")
    if not user_id:
        raise HTTPException(status_code=403, detail="user_id no encontrado en token")

    # ── Datos del usuario y saldo de billetera ──────────────────────────────
    user = await fetch_one(
        """
        SELECT u.id, u.alias, u.full_name, u.email, u.role,
               u.payout_country, u.created_at,
               COALESCE(w.balance_usdt, 0) AS balance_usdt
        FROM users u
        LEFT JOIN wallets w ON w.user_id = u.id
        WHERE u.id = %s
        """,
        (user_id,),
    )
    if not user:
        raise HTTPException(status_code=404, detail="Operador no encontrado")

    # ── Métricas de ganancias (hoy / mes / referidos) ──────────────────────
    # Centralizado en financial_reads (fuente única de verdad)
    metrics = await get_user_profit_metrics(user_id)

    # ── Ganancias desglosadas por país de origen ───────────────────────────
    profit_by_country = await fetch_all(
        """
        SELECT origin_country,
               COALESCE(SUM(profit_usdt), 0) AS total_profit_usdt,
               COUNT(*) AS order_count
        FROM orders
        WHERE operator_user_id = %s AND status = 'PAGADA'
        GROUP BY origin_country
        ORDER BY total_profit_usdt DESC
        """,
        (user_id,),
    )

    # ── Últimas 15 órdenes ─────────────────────────────────────────────────
    recent_orders = await fetch_all(
        """
        SELECT public_id, origin_country, dest_country,
               amount_origin, payout_dest, profit_usdt,
               status, created_at, paid_at
        FROM orders
        WHERE operator_user_id = %s
        ORDER BY created_at DESC
        LIMIT 15
        """,
        (user_id,),
    )

    # ── Últimos 10 retiros ─────────────────────────────────────────────────
    # Centralizado en financial_reads (fuente única de verdad)
    withdrawals = await get_user_withdrawals(user_id, limit=10)

    # ── Últimas 10 entradas del ledger ─────────────────────────────────────
    # Centralizado en financial_reads (fuente única de verdad)
    ledger = await get_user_ledger(user_id, limit=10)

    # ── Referidos (count) ──────────────────────────────────────────────────
    ref_row = await fetch_one(
        "SELECT COUNT(*) AS cnt FROM users WHERE sponsor_id = %s",
        (user_id,),
    )

    # ── Top 5 clientes frecuentes (gamificación) ───────────────────────────
    top_clients = await fetch_all(
        """
        SELECT beneficiary_text,
               COUNT(*) AS order_count,
               COALESCE(SUM(amount_origin), 0) AS total_sent,
               MAX(created_at) AS last_order_at
        FROM orders
        WHERE operator_user_id = %s
          AND status IN ('PAGADA', 'COMPLETADA')
          AND beneficiary_text IS NOT NULL
          AND beneficiary_text != ''
        GROUP BY beneficiary_text
        ORDER BY order_count DESC, last_order_at DESC
        LIMIT 5
        """,
        (user_id,),
    )

    # ── Meta mensual (configurable en settings) ────────────────────────────
    goal_row = await fetch_one(
        "SELECT value FROM settings WHERE key = 'monthly_goal_usdt' LIMIT 1"
    )
    monthly_goal = float(goal_row["value"]) if goal_row and goal_row.get("value") else 500.0

    # ── Trust Score del operador ───────────────────────────────────────────
    ts_row = await fetch_one(
        "SELECT COALESCE(trust_score, 50) AS trust_score FROM users WHERE id = %s",
        (user_id,),
    )
    trust_score = float(ts_row["trust_score"]) if ts_row else 50.0

    # ── Leaderboard: Top 10 operadores por trust_score ─────────────────────
    # Centralizado en financial_reads (fuente única de verdad)
    leaderboard = await get_operator_leaderboard(limit=10)

    # ── Órdenes completadas hoy ────────────────────────────────────────────
    orders_today_row = await fetch_one(
        """
        SELECT COUNT(*) AS cnt FROM orders
        WHERE operator_user_id = %s AND status = 'PAGADA'
          AND created_at >= date_trunc('day', now())
        """,
        (user_id,),
    )
    orders_today = int(orders_today_row["cnt"]) if orders_today_row else 0

    # ── Actividad 24h (para line chart) ────────────────────────────────────
    activity_24h = await fetch_all(
        """
        SELECT date_trunc('hour', created_at) AS hour,
               COUNT(*) AS order_count
        FROM orders
        WHERE operator_user_id = %s
          AND created_at >= now() - INTERVAL '24 hours'
        GROUP BY hour
        ORDER BY hour ASC
        """,
        (user_id,),
    )

    return {
        "ok": True,
        "user": _row(user),
        "wallet": {
            "balance_usdt": _s(user.get("balance_usdt")),
            "profit_today": _s(metrics.get("profit_today")) if metrics else "0.00",
            "profit_month": _s(metrics.get("profit_month")) if metrics else "0.00",
            "profit_total": _s(metrics.get("profit_total")) if metrics else "0.00",
            "referrals_month": _s(metrics.get("referrals_month")) if metrics else "0.00",
        },
        "monthly_goal": monthly_goal,
        "trust_score": trust_score,
        "orders_today": orders_today,
        "profit_by_country": [
            {
                "origin_country": r["origin_country"],
                "total_profit_usdt": _s(r["total_profit_usdt"]),
                "order_count": int(r["order_count"]),
            }
            for r in (profit_by_country or [])
        ],
        "top_clients": [
            {
                "name": r["beneficiary_text"],
                "order_count": int(r["order_count"]),
                "total_sent": _s(r["total_sent"]),
                "last_order_at": _s(r["last_order_at"]),
            }
            for r in (top_clients or [])
        ],
        "leaderboard": [
            {
                "alias": r["alias"],
                "full_name": r.get("full_name") or r["alias"],
                "trust_score": float(r["trust_score"]),
                "profit_month": _s(r["profit_month"]),
                "orders_month": int(r["orders_month"]),
                "kyc_status": r.get("kyc_status") or "PENDING",
                "is_me": int(r["id"]) == int(user_id),
            }
            for r in (leaderboard or [])
        ],
        "activity_24h": [
            {
                "hour": _s(r["hour"]),
                "order_count": int(r["order_count"]),
            }
            for r in (activity_24h or [])
        ],
        "recent_orders": _rows(recent_orders),
        "withdrawals": _rows(withdrawals),
        "ledger": _rows(ledger),
        "referrals_count": int(ref_row["cnt"]) if ref_row else 0,
    }
