from datetime import datetime, timedelta
from .db import fetch_one, fetch_all

def get_profit_daily(days: int = 30):
    """Obtiene profit por día en los últimos N días"""
    rows = fetch_all(
        """
        SELECT
            DATE(created_at) as day,
            COUNT(*) as total_orders,
            SUM(CASE WHEN status = 'PAGADA' THEN profit_usdt ELSE 0 END) as total_profit,
            SUM(CASE WHEN status = 'PAGADA' THEN amount_origin ELSE 0 END) as total_volume
        FROM orders
        WHERE created_at >= NOW() - make_interval(days => %s)
        GROUP BY DATE(created_at)
        ORDER BY day DESC
        """,
        (days,)
    )
    return rows

def get_stuck_orders():
    """Órdenes antiguas en estados intermedios"""
    stuck_origin = fetch_all(
        """
        SELECT public_id, created_at, status, origin_country
        FROM orders
        WHERE status = 'ORIGIN_VERIFYING'
          AND created_at < NOW() - make_interval(hours => 24)
        ORDER BY created_at ASC
        """
    )
    
    stuck_payment = fetch_all(
        """
        SELECT public_id, created_at, status, destination_country_code, awaiting_paid_proof_by
        FROM orders
        WHERE awaiting_paid_proof = true
          AND created_at < NOW() - make_interval(hours => 48)
        ORDER BY created_at ASC
        """
    )
    
    return {
        "stuck_origin_verification": stuck_origin,
        "stuck_payment_proof": stuck_payment
    }

def get_operators_ranking(days: int = 7):
    """Ranking de operadores por profit y cantidad"""
    rows = fetch_all(
        """
        SELECT
            paid_by_user_telegram_id,
            paid_by_user_name,
            COUNT(*) as orders_paid,
            SUM(profit_usdt) as total_profit
        FROM orders
        WHERE status = 'PAGADA'
          AND paid_at >= NOW() - make_interval(days => %s)
          AND paid_by_user_telegram_id IS NOT NULL
        GROUP BY paid_by_user_telegram_id, paid_by_user_name
        ORDER BY total_profit DESC
        """,
        (days,)
    )
    return rows
