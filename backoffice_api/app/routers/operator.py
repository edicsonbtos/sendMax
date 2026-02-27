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
def get_operator_dashboard(auth: dict = Depends(require_operator_or_admin)):
    """
    Dashboard personal del operador autenticado.
    Los datos siempre son filtrados por user_id del JWT (cada operador ve solo los suyos).
    """
    user_id = auth.get("user_id")
    if not user_id:
        raise HTTPException(status_code=403, detail="user_id no encontrado en token")

    # ── Datos del usuario y saldo de billetera ──────────────────────────────
    user = fetch_one(
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
    metrics = fetch_one(
        """
        SELECT
            COALESCE((
                SELECT SUM(amount_usdt) FROM wallet_ledger
                WHERE user_id = %s AND type = 'ORDER_PROFIT'
                  AND created_at >= date_trunc('day', now())
            ), 0) AS profit_today,
            COALESCE((
                SELECT SUM(amount_usdt) FROM wallet_ledger
                WHERE user_id = %s AND type = 'ORDER_PROFIT'
                  AND created_at >= date_trunc('month', now())
            ), 0) AS profit_month,
            COALESCE((
                SELECT SUM(amount_usdt) FROM wallet_ledger
                WHERE user_id = %s AND type = 'SPONSOR_COMMISSION'
                  AND created_at >= date_trunc('month', now())
            ), 0) AS referrals_month,
            COALESCE((
                SELECT SUM(amount_usdt) FROM wallet_ledger
                WHERE user_id = %s AND type = 'ORDER_PROFIT'
            ), 0) AS profit_total
        """,
        (user_id, user_id, user_id, user_id),
    )

    # ── Ganancias desglosadas por país de origen ───────────────────────────
    profit_by_country = fetch_all(
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
    recent_orders = fetch_all(
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
    withdrawals = fetch_all(
        """
        SELECT id, amount_usdt, status, dest_text, country,
               fiat, fiat_amount, reject_reason,
               created_at, resolved_at
        FROM withdrawals
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 10
        """,
        (user_id,),
    )

    # ── Últimas 10 entradas del ledger ─────────────────────────────────────
    ledger = fetch_all(
        """
        SELECT id, amount_usdt, type, ref_order_public_id, memo, created_at
        FROM wallet_ledger
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 10
        """,
        (user_id,),
    )

    # ── Referidos (count) ──────────────────────────────────────────────────
    ref_row = fetch_one(
        "SELECT COUNT(*) AS cnt FROM users WHERE sponsor_id = %s",
        (user_id,),
    )

    # ── Top 5 clientes frecuentes (gamificación) ───────────────────────────
    top_clients = fetch_all(
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
    goal_row = fetch_one(
        "SELECT value FROM settings WHERE key = 'monthly_goal_usdt' LIMIT 1"
    )
    monthly_goal = float(goal_row["value"]) if goal_row and goal_row.get("value") else 500.0

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
        "recent_orders": _rows(recent_orders),
        "withdrawals": _rows(withdrawals),
        "ledger": _rows(ledger),
        "referrals_count": int(ref_row["cnt"]) if ref_row else 0,
    }
