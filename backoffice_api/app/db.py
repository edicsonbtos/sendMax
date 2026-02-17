import os
import psycopg
from psycopg_pool import ConnectionPool
from dotenv import load_dotenv

load_dotenv()


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


# Pool global - se reutiliza en cada query
_pool_ro = None
_pool_rw = None


def _get_pool_ro() -> ConnectionPool:
    global _pool_ro
    if _pool_ro is None:
        _pool_ro = ConnectionPool(
            get_db_url_ro(),
            min_size=2,
            max_size=10,
            open=True,
        )
    return _pool_ro


def _get_pool_rw() -> ConnectionPool:
    global _pool_rw
    if _pool_rw is None:
        _pool_rw = ConnectionPool(
            get_db_url_rw(),
            min_size=1,
            max_size=5,
            open=True,
        )
    return _pool_rw


def fetch_one(sql: str, params: tuple = (), *, rw: bool = False):
    pool = _get_pool_rw() if rw else _get_pool_ro()
    with pool.connection() as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
        if rw:
            conn.commit()
        return row


def fetch_all(sql: str, params: tuple = ()):
    pool = _get_pool_ro()
    with pool.connection() as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(sql, params)
            return cur.fetchall()
