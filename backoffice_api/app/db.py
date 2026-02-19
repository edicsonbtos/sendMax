"""
DB helpers para Backoffice API (psycopg3 + psycopg_pool).

Objetivos:
- Pools RO y RW separados (si RW no existe, cae a RO).
- commit/rollback seguros.
- Retry ante fallos transitorios de red/SSL típicos de Neon pooler.
- Logging útil sin filtrar secretos.
"""

from __future__ import annotations

import os
import time
import logging
from typing import Any

import psycopg
from psycopg_pool import ConnectionPool
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


def get_db_url_ro() -> str:
    url = os.getenv("DATABASE_URL_RO") or os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL_RO o DATABASE_URL no esta configurada")
    return url


def get_db_url_rw() -> str:
    url = os.getenv("DATABASE_URL_RW")
    if not url:
        url = get_db_url_ro()
    return url


_pool_ro: ConnectionPool | None = None
_pool_rw: ConnectionPool | None = None


def _make_pool(dsn: str, *, min_size: int, max_size: int) -> ConnectionPool:
    # Nota: valores conservadores para Neon pooler (evitar conexiones viejas/idle).
    return ConnectionPool(
        dsn,
        min_size=min_size,
        max_size=max_size,
        open=True,
        timeout=10,          # tiempo máximo esperando conexión del pool
        max_lifetime=55 * 60,  # reciclar conexiones antes de 1h
        max_idle=5 * 60,       # cerrar conexiones idle > 5 min
    )


def _get_pool_ro() -> ConnectionPool:
    global _pool_ro
    if _pool_ro is None:
        _pool_ro = _make_pool(get_db_url_ro(), min_size=2, max_size=10)
        logger.info("DB pool RO inicializado")
    return _pool_ro


def _get_pool_rw() -> ConnectionPool:
    global _pool_rw
    if _pool_rw is None:
        _pool_rw = _make_pool(get_db_url_rw(), min_size=1, max_size=5)
        logger.info("DB pool RW inicializado")
    return _pool_rw


def _is_transient_operational_error(e: Exception) -> bool:
    if not isinstance(e, psycopg.OperationalError):
        return False
    msg = str(e).lower()
    needles = [
        "ssl connection has been closed unexpectedly",
        "server closed the connection unexpectedly",
        "connection reset by peer",
        "terminating connection",
        "broken pipe",
        "network is unreachable",
        "connection timed out",
    ]
    return any(n in msg for n in needles)


def fetch_one(sql: str, params: tuple = (), *, rw: bool = False) -> dict[str, Any] | None:
    """
    Ejecuta una query y retorna una fila como dict o None.
    rw=True: usa pool RW y hace commit.
    Incluye retry ante OperationalError transitorio.
    """
    pool = _get_pool_rw() if rw else _get_pool_ro()
    attempts = 2  # 1 reintento
    last_exc: Exception | None = None

    for i in range(attempts):
        try:
            with pool.connection() as conn:
                try:
                    with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                        cur.execute(sql, params)
                        row = cur.fetchone()
                        if rw:
                            conn.commit()
                        return row
                except Exception:
                    if rw:
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                    raise
        except Exception as e:
            last_exc = e
            if i < attempts - 1 and _is_transient_operational_error(e):
                logger.warning("DB transient OperationalError (retry %s/%s): %s", i + 1, attempts, e)
                time.sleep(0.15)
                continue
            logger.exception("fetch_one error (rw=%s): %s", rw, e)
            raise

    raise last_exc  # pragma: no cover


def fetch_all(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    """
    Ejecuta una query y retorna lista de filas como dicts.
    Incluye retry ante OperationalError transitorio.
    """
    pool = _get_pool_ro()
    attempts = 2
    last_exc: Exception | None = None

    for i in range(attempts):
        try:
            with pool.connection() as conn:
                with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                    cur.execute(sql, params)
                    return list(cur.fetchall())
        except Exception as e:
            last_exc = e
            if i < attempts - 1 and _is_transient_operational_error(e):
                logger.warning("DB transient OperationalError (retry %s/%s): %s", i + 1, attempts, e)
                time.sleep(0.15)
                continue
            logger.exception("fetch_all error: %s", e)
            raise

    raise last_exc  # pragma: no cover
