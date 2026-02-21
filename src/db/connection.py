# Version: 20260221-bot-db-startup-fix
from __future__ import annotations

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import psycopg
from psycopg_pool import AsyncConnectionPool

logger = logging.getLogger("db")

_pool: AsyncConnectionPool | None = None

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


def _is_transient(e: Exception) -> bool:
    if not isinstance(e, psycopg.OperationalError):
        return False
    msg = str(e).lower()
    return any(n in msg for n in _TRANSIENT_NEEDLES)


def _backoff_delay(attempt: int) -> float:
    if attempt < len(_BACKOFF_DELAYS):
        return _BACKOFF_DELAYS[attempt]
    return _BACKOFF_DELAYS[-1]


def _get_database_url() -> str:
    """Lee DATABASE_URL de env sin importar settings (evita ciclo circular)."""
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL no configurada en variables de entorno")

    # Forzar connect_timeout para evitar cuelgues en red/Neon
    if "connect_timeout" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}connect_timeout=10"

    return url


def get_pool() -> AsyncConnectionPool:
    """
    Pool async endurecido para Neon/Railway.
    """
    global _pool
    if _pool is None:
        logger.info("Creando pool de conexiones ASYNC DB (hardened)...")
        _pool = AsyncConnectionPool(
            _get_database_url(),
            min_size=1,
            max_size=10, # Aumentado para mayor concurrencia
            open=False, # Se abrirá explícitamente o al primer uso
            timeout=10,
            max_lifetime=300,      # 5 min
            max_idle=120,          # 2 min
            reconnect_timeout=5,
            check=AsyncConnectionPool.check_connection,
        )
    return _pool


async def open_pool() -> None:
    """Abre el pool de conexiones de forma explícita."""
    pool = get_pool()
    if not pool.opened:
        logger.info("Abriendo pool ASYNC DB...")
        await pool.open()
        logger.info("Pool ASYNC DB abierto")


def is_pool_open() -> bool:
    """Verifica si el pool existe y está abierto."""
    global _pool
    return bool(_pool) and bool(_pool.opened)


@asynccontextmanager
async def get_async_conn() -> AsyncGenerator[psycopg.AsyncConnection, None]:
    """
    Context manager asíncrono para conexiones.
    Incluye logging de tiempo de ejecución (Middleware de Diagnóstico).
    """
    pool = get_pool()
    start_time = time.perf_counter()

    # Asegurar que el pool esté abierto
    # AsyncConnectionPool.connection() abrirá el pool si no lo está,
    # pero es mejor ser explícitos si quisiéramos controlar el inicio.

    async with pool.connection() as conn:
        try:
            yield conn
        finally:
            elapsed = time.perf_counter() - start_time
            if elapsed > 2.0:
                logger.warning(f"SLOW QUERY DETECTED: {elapsed:.3f}s")
            elif elapsed > 0.5:
                logger.info(f"Query info: {elapsed:.3f}s")


async def close_pool() -> None:
    """Cerrar pool en shutdown (idempotente)."""
    global _pool
    if _pool is not None:
        try:
            await _pool.close()
            logger.info("DB async pool cerrado correctamente")
        except Exception:
            logger.exception("Error cerrando DB async pool")
        _pool = None


async def ping_db() -> bool:
    for attempt in range(_MAX_ATTEMPTS):
        try:
            async with get_async_conn() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1;")
                    await cur.fetchone()
            return True
        except Exception as e:
            if attempt < _MAX_ATTEMPTS - 1 and _is_transient(e):
                await asyncio.sleep(_backoff_delay(attempt))
                continue
            logger.exception("DB ping failed: %s", e)
            return False
    return False

# Mantener get_conn sync para compatibilidad temporal si es necesario,
# pero idealmente migrar todo a get_async_conn.
# Por ahora lo dejamos para no romper el arranque hasta migrar repos.
def get_conn():
    # ADVERTENCIA: Esto es síncrono y usa un pool que ahora queremos que sea async.
    # Necesitamos una transición suave.
    # Si psycopg_pool.AsyncConnectionPool se usa con código sync fallará.
    # Por ahora, mantendremos el pool sync disponible si es necesario,
    # pero el objetivo es borrarlo.
    raise RuntimeError("Usar get_async_conn() en lugar de get_conn()")
