from __future__ import annotations

import psycopg
from src.config.settings import settings


def get_conn():
    return psycopg.connect(settings.DATABASE_URL)


def touch_contact(telegram_user_id: int) -> None:
    """
    Guarda telegram_user_id para broadcast/post-reset.
    Idempotente: si ya existe, actualiza last_seen_at.
    """
    sql = """
    INSERT INTO user_contacts (telegram_user_id, first_seen_at, last_seen_at)
    VALUES (%s, now(), now())
    ON CONFLICT (telegram_user_id)
    DO UPDATE SET last_seen_at = now();
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (int(telegram_user_id),))
        conn.commit()


def list_all_telegram_ids(limit: int | None = None) -> list[int]:
    sql = "SELECT telegram_user_id FROM user_contacts ORDER BY last_seen_at DESC"
    if limit is not None:
        sql += " LIMIT %s"
    with get_conn() as conn:
        with conn.cursor() as cur:
            if limit is None:
                cur.execute(sql)
            else:
                cur.execute(sql, (int(limit),))
            return [int(r[0]) for r in cur.fetchall()]
