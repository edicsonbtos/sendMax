from __future__ import annotations

from dataclasses import dataclass

from src.db.connection import get_async_conn


@dataclass(frozen=True)
class ReferralRow:
    id: int
    alias: str
    created_at: object


async def count_referrals(sponsor_user_id: int) -> int:
    sql = "SELECT COUNT(*) FROM users WHERE sponsor_id = %s;"
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (sponsor_user_id,))
            rows = await cur.fetchall()
            return int(rows[0][0]) if rows else 0


async def list_recent_referrals(sponsor_user_id: int, limit: int = 10) -> list[ReferralRow]:
    sql = """
        SELECT id, alias, created_at
        FROM users
        WHERE sponsor_id = %s
        ORDER BY created_at DESC
        LIMIT %s;
    """
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (sponsor_user_id, limit))
            res = await cur.fetchall()
            return [ReferralRow(*r) for r in res]
