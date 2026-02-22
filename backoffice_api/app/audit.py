"""Audit helpers: profit daily, operators ranking, corridors, stuck orders"""

from datetime import date, timedelta
from .db import fetch_one, fetch_all


def get_profit_daily(days: int = 30):
    """Profit por dia en los ultimos N dias (rellena dias sin datos con 0)."""
    rows = fetch_all(
        """
        SELECT
            DATE(paid_at) AS day,
            COUNT(*) AS total_orders,
            COALESCE(SUM(profit_usdt), 0) AS total_profit,
            COALESCE(SUM(profit_real_usdt), 0) AS total_profit_real,
            COALESCE(SUM(amount_origin), 0) AS total_volume
        FROM orders
        WHERE status = 'PAGADA'
          AND paid_at >= (CURRENT_DATE - (%s::int - 1) * INTERVAL '1 day')
        GROUP BY DATE(paid_at)
        ORDER BY day ASC
        """,
        (days,),
    )

    m = {}
    for r in rows:
        k = str(r["day"])
        m[k] = {
            "day": k,
            "total_orders": int(r["total_orders"] or 0),
            "total_profit": float(r["total_profit"] or 0),
            "total_profit_real": float(r["total_profit_real"] or 0),
            "total_volume": float(r["total_volume"] or 0),
        }

    out = []
    start = date.today() - timedelta(days=days - 1)
    for i in range(days):
        d = start + timedelta(days=i)
        k = str(d)
        out.append(m.get(k, {
            "day": k,
            "total_orders": 0,
            "total_profit": 0.0,
            "total_profit_real": 0.0,
            "total_volume": 0.0,
        }))

    return out


def get_operators_ranking(days: int = 7):
    """Ranking de operadores por profit y cantidad de ordenes pagadas.

    Usa origin_verified_by_telegram_id como identificador del operador
    que verifico y proceso la orden.
    """
    rows = fetch_all(
        """
        SELECT
            origin_verified_by_telegram_id AS telegram_id,
            COALESCE(origin_verified_by_name, 'Operador ' || origin_verified_by_telegram_id::text) AS name,
            COUNT(*) AS orders_paid,
            COALESCE(SUM(profit_usdt), 0) AS total_profit,
            COALESCE(SUM(profit_real_usdt), 0) AS total_profit_real,
            COALESCE(SUM(amount_origin), 0) AS total_volume,
            COALESCE(AVG(profit_usdt), 0) AS avg_profit,
            COUNT(DISTINCT origin_country) AS countries_operated,
            COUNT(DISTINCT dest_country) AS dest_countries,
            MIN(paid_at) AS first_paid,
            MAX(paid_at) AS last_paid
        FROM orders
        WHERE status = 'PAGADA'
          AND paid_at >= (CURRENT_DATE - (%s::int - 1) * INTERVAL '1 day')
          AND origin_verified_by_telegram_id IS NOT NULL
        GROUP BY origin_verified_by_telegram_id, origin_verified_by_name
        ORDER BY total_profit DESC
        LIMIT 20
        """,
        (days,),
    )

    out = []
    for r in rows:
        out.append({
            "telegram_id": r["telegram_id"],
            "name": r["name"],
            "orders_paid": int(r["orders_paid"] or 0),
            "total_profit": float(r["total_profit"] or 0),
            "total_profit_real": float(r["total_profit_real"] or 0),
            "total_volume": float(r["total_volume"] or 0),
            "avg_profit": float(r["avg_profit"] or 0),
            "countries_operated": int(r["countries_operated"] or 0),
            "dest_countries": int(r["dest_countries"] or 0),
            "first_paid": r["first_paid"].isoformat() if r["first_paid"] else None,
            "last_paid": r["last_paid"].isoformat() if r["last_paid"] else None,
        })

    return out


def get_corridors(days: int = 30):
    """Analisis por corredor (origin->dest) con profit y volumen."""
    rows = fetch_all(
        """
        SELECT
            origin_country,
            dest_country,
            COUNT(*) AS order_count,
            COALESCE(SUM(profit_usdt), 0) AS total_profit,
            COALESCE(SUM(profit_real_usdt), 0) AS total_profit_real,
            COALESCE(SUM(amount_origin), 0) AS total_volume_origin,
            COALESCE(SUM(payout_dest), 0) AS total_volume_dest,
            COALESCE(AVG(profit_usdt), 0) AS avg_profit,
            COUNT(*) FILTER (WHERE status = 'PAGADA') AS paid_count,
            COUNT(*) FILTER (WHERE status = 'CANCELADA') AS cancelled_count
        FROM orders
        WHERE created_at >= (CURRENT_DATE - (%s::int - 1) * INTERVAL '1 day')
        GROUP BY origin_country, dest_country
        ORDER BY total_profit DESC
        """,
        (days,),
    )

    out = []
    for r in rows:
        out.append({
            "origin_country": r["origin_country"],
            "dest_country": r["dest_country"],
            "corridor": r["origin_country"] + " -> " + r["dest_country"],
            "order_count": int(r["order_count"] or 0),
            "total_profit": float(r["total_profit"] or 0),
            "total_profit_real": float(r["total_profit_real"] or 0),
            "total_volume_origin": float(r["total_volume_origin"] or 0),
            "total_volume_dest": float(r["total_volume_dest"] or 0),
            "avg_profit": float(r["avg_profit"] or 0),
            "paid_count": int(r["paid_count"] or 0),
            "cancelled_count": int(r["cancelled_count"] or 0),
            "conversion_rate": round(
                (int(r["paid_count"] or 0) / int(r["order_count"] or 1)) * 100, 1
            ),
        })

    return out


def get_stuck_orders():
    """Ordenes antiguas en estados intermedios."""
    stuck_origin = fetch_one(
        """
        SELECT COUNT(*) AS count
        FROM orders
        WHERE status = 'ORIGEN_VERIFICANDO'
          AND created_at < NOW() - INTERVAL '24 hours'
        """
    )

    stuck_payment = fetch_one(
        """
        SELECT COUNT(*) AS count
        FROM orders
        WHERE awaiting_paid_proof = true
          AND created_at < NOW() - INTERVAL '48 hours'
        """
    )

    return {
        "stuck_origin_verification_count": int(stuck_origin["count"]) if stuck_origin else 0,
        "stuck_payment_proof_count": int(stuck_payment["count"]) if stuck_payment else 0,
    }
