"""
Repositorio de tasas (rates).

Responsabilidad:
- Guardar una versión efectiva de tasas (rate_versions)
- Guardar precios BUY/SELL por país usados en esa versión (p2p_country_prices)
- Guardar tasas por ruta para esa versión (route_rates)
- Leer la última versión activa para mostrar "📈 Tasas" en el bot

Changelog:
- Migracion a ASYNC para Fase 2.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from src.db.connection import get_async_conn

# --- Modelos simples (DTOs) ---

@dataclass(frozen=True)
class RateVersion:
    id: int
    kind: str
    reason: str | None
    created_at: datetime
    effective_from: datetime
    effective_to: datetime | None
    is_active: bool


@dataclass(frozen=True)
class RouteRate:
    origin_country: str
    dest_country: str
    commission_pct: Decimal
    buy_origin: Decimal
    sell_dest: Decimal
    rate_base: Decimal
    rate_client: Decimal


@dataclass(frozen=True)
class CountryPrice:
    country: str
    fiat: str
    buy_price: Decimal
    sell_price: Decimal


# get_async_conn importado desde connection.py (pool centralizado)


# --- Escritura ---

async def create_rate_version(
    *,
    kind: str,
    effective_from: datetime,
    reason: str | None = None,
    is_active: bool = True,
) -> int:
    sql = """
        INSERT INTO rate_versions (kind, reason, effective_from, is_active)
        VALUES (%s, %s, %s, %s)
        RETURNING id;
    """
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (kind, reason, effective_from, is_active))
            res = await cur.fetchone()
            await conn.commit()
            return int(res[0]) if res else 0


async def deactivate_all_rate_versions() -> None:
    sql = "UPDATE rate_versions SET is_active = false WHERE is_active = true;"
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql)
            await conn.commit()


async def activate_rate_version(rate_version_id: int) -> None:
    sql = "UPDATE rate_versions SET is_active = true WHERE id = %s;"
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (rate_version_id,))
            await conn.commit()


async def insert_country_price(
    *,
    rate_version_id: int,
    country: str,
    fiat: str,
    buy_price: Decimal,
    sell_price: Decimal,
    methods_used: str | None,
    amount_ref: Decimal | None,
    source: str,
    is_verified: bool,
) -> None:
    sql = """
        INSERT INTO p2p_country_prices (
            rate_version_id, country, fiat,
            buy_price, sell_price,
            methods_used, amount_ref,
            source, is_verified
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s);
    """
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                sql,
                (
                    rate_version_id,
                    country, fiat,
                    buy_price, sell_price,
                    methods_used, amount_ref,
                    source, is_verified,
                ),
            )
            await conn.commit()


async def insert_route_rate(
    *,
    rate_version_id: int,
    origin_country: str,
    dest_country: str,
    commission_pct: Decimal,
    buy_origin: Decimal,
    sell_dest: Decimal,
    rate_base: Decimal,
    rate_client: Decimal,
) -> None:
    sql = """
        INSERT INTO route_rates (
            rate_version_id,
            origin_country, dest_country,
            commission_pct,
            buy_origin, sell_dest,
            rate_base, rate_client
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s);
    """
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                sql,
                (
                    rate_version_id,
                    origin_country, dest_country,
                    commission_pct,
                    buy_origin, sell_dest,
                    rate_base, rate_client,
                ),
            )
            await conn.commit()


# --- Lectura ---

async def get_latest_active_rate_version() -> RateVersion | None:
    sql = """
        SELECT id, kind, reason, created_at, effective_from, effective_to, is_active
        FROM rate_versions
        WHERE is_active = true
        ORDER BY effective_from DESC
        LIMIT 1;
    """
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql)
            rows = await cur.fetchall()
            if not rows:
                return None
            return RateVersion(*rows[0])


async def get_route_rate(
    *,
    rate_version_id: int,
    origin_country: str,
    dest_country: str,
) -> RouteRate | None:
    sql = """
        SELECT origin_country, dest_country, commission_pct,
               buy_origin, sell_dest, rate_base, rate_client
        FROM route_rates
        WHERE rate_version_id = %s
          AND origin_country = %s
          AND dest_country = %s
        LIMIT 1;
    """
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (rate_version_id, origin_country, dest_country))
            rows = await cur.fetchall()
            if not rows:
                return None
            return RouteRate(*rows[0])


async def list_route_rates_for_version(
    *,
    rate_version_id: int,
    routes: list[tuple[str, str]],
) -> list[RouteRate]:
    """
    Devuelve RouteRate para un listado específico de rutas.
    """
    if not routes:
        return []

    clauses = []
    params = [rate_version_id]
    for (o, d) in routes:
        clauses.append("(origin_country = %s AND dest_country = %s)")
        params.extend([o, d])

    sql = f"""
        SELECT origin_country, dest_country, commission_pct,
               buy_origin, sell_dest, rate_base, rate_client
        FROM route_rates
        WHERE rate_version_id = %s
          AND ({' OR '.join(clauses)});
    """

    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, params)
            rows = await cur.fetchall()
            return [RouteRate(*r) for r in rows]


async def list_all_route_pairs_for_version(
    *,
    rate_version_id: int,
) -> list[tuple[str, str]]:
    """
    Devuelve todas las parejas (origin, dest) existentes para esa versión.
    """
    sql = """
        SELECT origin_country, dest_country
        FROM route_rates
        WHERE rate_version_id = %s;
    """
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (rate_version_id,))
            res = await cur.fetchall()
            return [(r[0], r[1]) for r in res]


async def get_country_price_for_version(*, rate_version_id: int, country: str) -> CountryPrice | None:
    sql = """
        SELECT country, fiat, buy_price, sell_price
        FROM p2p_country_prices
        WHERE rate_version_id = %s
          AND country = %s
        LIMIT 1;
    """
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (rate_version_id, country))
            rows = await cur.fetchall()
            if not rows:
                return None
            return CountryPrice(*rows[0])


async def get_latest_active_country_sell(*, country: str) -> tuple[str, Decimal] | None:
    """
    Returns (fiat, sell_price) for country using latest active rate_version.
    """
    rv = await get_latest_active_rate_version()
    if not rv:
        return None
    cp = await get_country_price_for_version(rate_version_id=rv.id, country=country)
    if not cp:
        return None
    return (cp.fiat, cp.sell_price)

async def list_route_rates_by_origin(
    *,
    rate_version_id: int,
    origin_country: str,
) -> list[RouteRate]:
    """
    Devuelve todas las rutas salientes de un país (origin -> *)
    para una versión de tasas.
    """
    sql = """
        SELECT origin_country, dest_country, commission_pct,
               buy_origin, sell_dest, rate_base, rate_client
        FROM route_rates
        WHERE rate_version_id = %s
          AND origin_country = %s
        ORDER BY dest_country ASC;
    """
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (rate_version_id, origin_country))
            rows = await cur.fetchall()
            return [RouteRate(*r) for r in rows]
