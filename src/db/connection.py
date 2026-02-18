import logging
import psycopg
from psycopg_pool import ConnectionPool
from src.config.settings import settings

logger = logging.getLogger("db")

_pool = None


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        logger.info("Creando pool de conexiones DB...")
        _pool = ConnectionPool(
            settings.DATABASE_URL,
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
