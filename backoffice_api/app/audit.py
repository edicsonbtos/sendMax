from datetime import date, timedelta
from .db import fetch_one, fetch_all

def get_profit_daily(days: int = 30):
    """Obtiene profit por día en los últimos N días (rellena días faltantes con 0)."""
    rows = fetch_all(
        """
        SELECT
            DATE(created_at) as day,
            COUNT(*) as total_orders,
            COALESCE(SUM(CASE WHEN status = 'PAGADA' THEN profit_usdt ELSE 0 END), 0) as total_profit,
            COALESCE(SUM(CASE WHEN status = 'PAGADA' THEN amount_origin ELSE 0 END), 0) as total_volume
        FROM orders
        WHERE created_at >= (CURRENT_DATE - (%s::int - 1) * INTERVAL '1 day')
        GROUP BY DATE(created_at)
        ORDER BY day ASC
        """,
        (days,)
    )

    # map day -> row
    m = {}
    for r in rows:
        k = str(r["day"])
        m[k] = {
            "day": k,
            "total_orders": int(r["total_orders"] or 0),
            "total_profit": float(r["total_profit"] or 0),
            "total_volume": float(r["total_volume"] or 0),
        }

    out = []
    start = date.today() - timedelta(days=days - 1)
    for i in range(days):
        d = start + timedelta(days=i)
        k = str(d)
        out.append(m.get(k, {"day": k, "total_orders": 0, "total_profit": 0.0, "total_volume": 0.0}))

    return out

def get_stuck_orders():
    """Órdenes antiguas en estados intermedios"""
    # Simplificado: solo contar, no traer detalles
    stuck_origin = fetch_one(
        """
        SELECT COUNT(*) as count
        FROM orders
        WHERE status = 'ORIGIN_VERIFYING'
          AND created_at < NOW() - INTERVAL '24 hours'
        """
    )

    stuck_payment = fetch_one(
        """
        SELECT COUNT(*) as count
        FROM orders
        WHERE awaiting_paid_proof = true
          AND created_at < NOW() - INTERVAL '48 hours'
        """
    )

    return {
        "stuck_origin_verification_count": stuck_origin["count"] if stuck_origin else 0,
        "stuck_payment_proof_count": stuck_payment["count"] if stuck_payment else 0
    }

def get_operators_ranking(days: int = 7):
    """Ranking de operadores por profit y cantidad"""
    # Verificar primero si hay datos
    count = fetch_one("SELECT COUNT(*) as total FROM orders WHERE status = 'PAGADA' AND paid_by_user_telegram_id IS NOT NULL")

    if not count or count["total"] == 0:
        return []

    rows = fetch_all(
        """
        SELECT
            paid_by_user_telegram_id as telegram_id,
            paid_by_user_name as name,
            COUNT(*) as orders_paid,
            SUM(profit_usdt) as total_profit
        FROM orders
        WHERE status = 'PAGADA'
          AND paid_at >= (CURRENT_DATE - (%s::int - 1) * INTERVAL '1 day')
          AND paid_by_user_telegram_id IS NOT NULL
        GROUP BY paid_by_user_telegram_id, paid_by_user_name
        ORDER BY total_profit DESC
        """,
        (days,)
    )
    return rows
