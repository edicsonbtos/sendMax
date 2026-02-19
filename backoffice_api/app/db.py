"""
Pool de conexiones para backoffice API.
- Pool RO (lectura) y Pool RW (escritura) separados.
- Manejo de errores con rollback y logging.
- Commit dentro del cursor para psycopg3.
"""

import os
import logging
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


# Pool global
_pool_ro: ConnectionPool | None = None
_pool_rw: ConnectionPool | None = None


def init_pools() -> None:
    """Inicializa ambos pools. Llamar en startup de la app."""
    global _pool_ro, _pool_rw
    if _pool_ro is None:
        _pool_ro = ConnectionPool(
            get_db_url_ro(),
            min_size=2,
            max_size=10,
            open=True,
        )
        logger.info("Pool RO inicializado")
    if _pool_rw is None:
        _pool_rw = ConnectionPool(
            get_db_url_rw(),
            min_size=1,
            max_size=5,
            open=True,
        )
        logger.info("Pool RW inicializado")


def _get_pool_ro() -> ConnectionPool:
    global _pool_ro
    if _pool_ro is None:
        init_pools()
    return _pool_ro


def _get_pool_rw() -> ConnectionPool:
    global _pool_rw
    if _pool_rw is None:
        init_pools()
    return _pool_rw


def fetch_one(sql: str, params: tuple = (), *, rw: bool = False):
    """
    Ejecuta query y retorna una fila como dict.
    Si rw=True usa pool RW y hace commit.
    """
    pool = _get_pool_rw() if rw else _get_pool_ro()
    try:
        with pool.connection() as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute(sql, params)
                row = cur.fetchone()
                if rw:
                    conn.commit()
                return row
    except Exception as e:
        logger.exception("fetch_one error (rw=%s): %s", rw, e)
        raise


def fetch_all(sql: str, params: tuple = (), *, rw: bool = False):
    """
    Ejecuta query y retorna lista de dicts.
    Si rw=True usa pool RW y hace commit.
    """
    pool = _get_pool_rw() if rw else _get_pool_ro()
    try:
        with pool.connection() as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
                if rw:
                    conn.commit()
                return rows
    except Exception as e:
        logger.exception("fetch_all error (rw=%s): %s", rw, e)
        raise
