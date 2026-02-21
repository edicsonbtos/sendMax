from __future__ import annotations

from src.db.connection import get_async_conn


async def touch_contact(telegram_user_id: int) -> None:
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
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (int(telegram_user_id),))
        await conn.commit()


async def list_all_telegram_ids(limit: int | None = None) -> list[int]:
    sql = "SELECT telegram_user_id FROM user_contacts ORDER BY last_seen_at DESC"
    if limit is not None:
        sql += " LIMIT %s"
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            if limit is None:
                await cur.execute(sql)
            else:
                await cur.execute(sql, (int(limit),))
            res = await cur.fetchall()
            return [int(r[0]) for r in res]
