from __future__ import annotations

from dataclasses import dataclass
import psycopg

from src.config.settings import settings


@dataclass(frozen=True)
class ReferralRow:
    id: int
    alias: str
    created_at: object


def get_conn():
    return psycopg.connect(settings.DATABASE_URL)


def count_referrals(sponsor_user_id: int) -> int:
    sql = "SELECT COUNT(*) FROM users WHERE sponsor_id = %s;"
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (sponsor_user_id,))
            return int(cur.fetchone()[0])


def list_recent_referrals(sponsor_user_id: int, limit: int = 10) -> list[ReferralRow]:
    sql = """
        SELECT id, alias, created_at
        FROM users
        WHERE sponsor_id = %s
        ORDER BY created_at DESC
        LIMIT %s;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (sponsor_user_id, limit))
            return [ReferralRow(*r) for r in cur.fetchall()]
