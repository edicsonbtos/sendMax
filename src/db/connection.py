# Version: 20260220-bot-db-hardened-async
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


async def open_pool() -> None:
    """Abre el pool de conexiones de forma explícita e idempotente."""
    pool = get_pool()
    # pool.open() es idempotente; si ya está abierto no hace nada.
    # Evitamos el check de 'pool.closed' porque en algunas versiones
    # puede no reflejar fielmente si el pool está listo para usarse.
    logger.info("Abriendo pool ASYNC DB...")
    await pool.open()
    logger.info("Pool ASYNC DB abierto")


def is_pool_open() -> bool:
    """Retorna True si el pool está inicializado y efectivamente abierto."""
    global _pool
    if _pool is None or _pool.closed:
        return False
    # _opened es un atributo interno de psycopg_pool que indica si se llamó a open()
    return getattr(_pool, "_opened", False)


async def wait_db_ready() -> None:
    """
    Garantiza que el pool esté abierto y responde a un ping.
    Lanza RuntimeError si no se logra tras reintentos (fail-fast).
    """
    await open_pool()
    # ping_db ya incluye reintentos y backoff internamente.
    if not await ping_db():
        raise RuntimeError("La base de datos no respondió al ping inicial tras varios reintentos (fail-fast)")


async def close_pool() -> None:
    """Cerrar pool en shutdown."""
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
