from __future__ import annotations

from decimal import Decimal

from src.db.connection import get_async_conn


async def load_country_prices_for_version(rate_version_id: int) -> dict[str, dict[str, object]]:
    """
    Devuelve precios BUY/SELL por país para una versión.
    Estructura:
      {
        "USA": {"buy": Decimal(...), "sell": Decimal(...), "is_verified": bool},
        ...
      }
    """
    sql = """
        SELECT country, buy_price, sell_price, is_verified
        FROM p2p_country_prices
        WHERE rate_version_id = %s;
    """
    out: dict[str, dict[str, object]] = {}
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (rate_version_id,))
            res = await cur.fetchall()
            for country, buy_price, sell_price, is_verified in res:
                out[str(country)] = {
                    "buy": Decimal(str(buy_price)),
                    "sell": Decimal(str(sell_price)),
                    "is_verified": bool(is_verified),
                }
    return out


async def latest_9am_version_id_today() -> int | None:
    """
    Busca la última versión baseline del día (kind='auto_9am') en hora local VET.
    Simplificación: usamos created_at/effective_from en UTC, y tomamos la más reciente de kind auto_9am.
    (Luego lo refinamos si quieres exactitud por fecha VET).
    """
    sql = """
        SELECT id
        FROM rate_versions
        WHERE kind = 'auto_9am'
        ORDER BY effective_from DESC
        LIMIT 1;
    """
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql)
            rows = await cur.fetchall()
            return int(rows[0][0]) if rows else None
