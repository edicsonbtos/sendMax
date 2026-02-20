# Version: 20260220-bot-db-hardened
from __future__ import annotations

import os
import time
import logging
from typing import Optional

import psycopg
from psycopg_pool import ConnectionPool

logger = logging.getLogger("db")

_pool: ConnectionPool | None = None

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


def get_pool() -> ConnectionPool:
    """
    Pool endurecido para Neon/Railway:
    - Recicla conexiones antes de que Neon las mate (max_lifetime)
    - Cierra conexiones idle (max_idle)
    - Timeouts para no colgar handlers
    """
    global _pool
    if _pool is None:
        logger.info("Creando pool de conexiones DB (hardened)...")
        _pool = ConnectionPool(
            _get_database_url(),
            min_size=1,
            max_size=5,
            open=True,
            timeout=10,
            max_lifetime=300,      # 5 min
            max_idle=120,          # 2 min
            reconnect_timeout=5,
        )
    return _pool


def get_conn():
    """
    Retorna conexion del pool. Usar:
      with get_conn() as conn:
        ...
    Nota: psycopg_pool descarta conexiones BAD automáticamente.
    """
    return get_pool().connection()


def close_pool() -> None:
    """Cerrar pool en shutdown (evita hilos colgados y conexiones zombie)."""
    global _pool
    if _pool is not None:
        try:
            _pool.close()
            logger.info("DB pool cerrado correctamente")
        except Exception:
            logger.exception("Error cerrando DB pool")
        _pool = None


def ping_db() -> bool:
    for attempt in range(_MAX_ATTEMPTS):
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1;")
                    cur.fetchone()
            return True
        except Exception as e:
            if attempt < _MAX_ATTEMPTS - 1 and _is_transient(e):
                time.sleep(_backoff_delay(attempt))
                continue
            logger.exception("DB ping failed: %s", e)
            return False
    return False