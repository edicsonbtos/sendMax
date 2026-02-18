# Version: 20260218-140638
import logging
import os
import psycopg
from psycopg_pool import ConnectionPool

logger = logging.getLogger("db")

_pool = None


def _get_database_url() -> str:
    """Lee DATABASE_URL de env sin importar settings (evita ciclo circular)"""
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL no configurada en variables de entorno")
    return url


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        logger.info("Creando pool de conexiones DB...")
        _pool = ConnectionPool(
            _get_database_url(),
            min_size=2,
            max_size=10,
            open=True,
        )
    return _pool


def get_conn():
    """Retorna conexion del pool. Usar con 'with get_conn() as conn:'"""
    return get_pool().connection()


def ping_db() -> bool:
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
        return True
    except Exception as e:
        logger.exception("DB ping failed: %s", e)
        return False
