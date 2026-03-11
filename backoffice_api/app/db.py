"""
DB helpers para Backoffice API (psycopg3 + psycopg_pool).

Pools RO y RW separados.
Retry con backoff exponencial ante fallos transitorios de Neon.
"""

from __future__ import annotations

import os
import asyncio
import logging
from typing import Any, Callable, TypeVar

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# -- Config --

_MAX_ATTEMPTS = 3
_BACKOFF_DELAYS = [0.2, 0.8, 2.0]

_TRANSIENT_NEEDLES = [
    "ssl connection has been closed unexpectedly",
    "server closed the connection unexpectedly",
    "connection reset by peer",
    "terminating connection",
    "broken pipe",
    "network is unreachable",
    "connection timed out",
    "timeout expired",
    "could not translate host name",
    "could not connect to server",
    "connection refused",
    "the database system is starting up",
    "too many clients already",
]


def get_db_url_ro() -> str:
    url = os.getenv("DATABASE_URL_RO") or os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL_RO o DATABASE_URL no esta configurada")
    if "connect_timeout" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}connect_timeout=10"
    return url


def get_db_url_rw() -> str:
    url = os.getenv("DATABASE_URL_RW")
    if not url:
        url = get_db_url_ro()
    if "connect_timeout" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}connect_timeout=10"
    return url


# -- Pool management --

_pool_ro: AsyncConnectionPool | None = None
_pool_rw: AsyncConnectionPool | None = None


def _make_pool(dsn: str, *, min_size: int, max_size: int) -> AsyncConnectionPool:
    return AsyncConnectionPool(
        dsn,
        min_size=min_size,
        max_size=max_size,
        open=True,
        timeout=10,
        max_lifetime=300,
        max_idle=120,
        reconnect_timeout=5,
    )


def _get_pool_ro() -> AsyncConnectionPool:
    global _pool_ro
    if _pool_ro is None:
        _pool_ro = _make_pool(get_db_url_ro(), min_size=1, max_size=5)
        logger.info("DB pool RO inicializado (min=1, max=5)")
    return _pool_ro


def _get_pool_rw() -> AsyncConnectionPool:
    global _pool_rw
    if _pool_rw is None:
        _pool_rw = _make_pool(get_db_url_rw(), min_size=1, max_size=3)
        logger.info("DB pool RW inicializado (min=1, max=3)")
    return _pool_rw


# -- Transient error detection --

def _is_transient(e: Exception) -> bool:
    if not isinstance(e, psycopg.OperationalError):
        return False
    msg = str(e).lower()
    return any(n in msg for n in _TRANSIENT_NEEDLES)


def _backoff_delay(attempt: int) -> float:
    if attempt < len(_BACKOFF_DELAYS):
        return _BACKOFF_DELAYS[attempt]
    return _BACKOFF_DELAYS[-1]


# -- Query helpers --

async def fetch_one(
    sql: str,
    params: tuple = (),
    *,
    rw: bool = False,
) -> dict[str, Any] | None:
    pool = _get_pool_rw() if rw else _get_pool_ro()
    last_exc: Exception | None = None

    for attempt in range(_MAX_ATTEMPTS):
        try:
            async with pool.connection() as conn:
                try:
                    async with conn.cursor(row_factory=dict_row) as cur:
                        await cur.execute(sql, params)
                        row = await cur.fetchone()
                        if rw:
                            await conn.commit()
                        return row
                except Exception:
                    if rw:
                        try:
                            await conn.rollback()
                        except Exception:
                            pass
                    raise
        except Exception as e:
            last_exc = e
            if attempt < _MAX_ATTEMPTS - 1 and _is_transient(e):
                delay = _backoff_delay(attempt)
                logger.warning(
                    "DB transient error (attempt %d/%d, retry in %.1fs): %s",
                    attempt + 1, _MAX_ATTEMPTS, delay, e,
                )
                await asyncio.sleep(delay)
                continue
            logger.exception("fetch_one failed (rw=%s, attempt %d): %s", rw, attempt + 1, e)
            raise

    raise last_exc


async def fetch_all(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    pool = _get_pool_ro()
    last_exc: Exception | None = None

    for attempt in range(_MAX_ATTEMPTS):
        try:
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(sql, params)
                    return list(await cur.fetchall())
        except Exception as e:
            last_exc = e
            if attempt < _MAX_ATTEMPTS - 1 and _is_transient(e):
                delay = _backoff_delay(attempt)
                logger.warning(
                    "DB transient error (attempt %d/%d, retry in %.1fs): %s",
                    attempt + 1, _MAX_ATTEMPTS, delay, e,
                )
                await asyncio.sleep(delay)
                continue
            logger.exception("fetch_all failed (attempt %d): %s", attempt + 1, e)
            raise

    raise last_exc


async def close_pools() -> None:
    global _pool_ro, _pool_rw
    for label, pool in [("RO", _pool_ro), ("RW", _pool_rw)]:
        if pool is not None:
            try:
                await pool.close()
                logger.info("DB pool %s cerrado", label)
            except Exception as e:
                logger.warning("Error cerrando pool %s: %s", label, e)
    _pool_ro = None
    _pool_rw = None

# ============================================================
# Transaccion atomica RW con advisory lock support
# ============================================================

_T = TypeVar('_T')

async def run_in_transaction(fn: Callable[[psycopg.AsyncCursor], _T], *, attempts=_MAX_ATTEMPTS) -> _T:
    pool = _get_pool_rw()
    last_exc = None

    for attempt in range(attempts):
        try:
            async with pool.connection() as conn:
                try:
                    async with conn.cursor(row_factory=dict_row) as cur:
                        if asyncio.iscoroutinefunction(fn):
                            result = await fn(cur)
                        else:
                            result = fn(cur)
                        await conn.commit()
                        return result
                except BaseException:
                    try:
                        await conn.rollback()
                    except Exception:
                        pass
                    raise
        except Exception as e:
            last_exc = e
            if attempt < attempts - 1 and _is_transient(e):
                delay = _backoff_delay(attempt)
                logger.warning(
                    "run_in_transaction retry %d/%d in %.1fs: %s",
                    attempt + 1, attempts, delay, e,
                )
                await asyncio.sleep(delay)
                continue
            if isinstance(e, psycopg.OperationalError):
                logger.exception(
                    "run_in_transaction failed (attempt %d): %s",
                    attempt + 1, e,
                )
            raise

    raise last_exc
