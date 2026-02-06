import os
import psycopg
from dotenv import load_dotenv

# En prod Railway no usa .env; en local sí
load_dotenv()

def get_db_url_ro() -> str:
    url = os.getenv("DATABASE_URL_RO") or os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL_RO o DATABASE_URL no está configurada")
    return url

def get_db_url_rw() -> str:
    url = os.getenv("DATABASE_URL_RW")
    if not url:
        # fallback: si no hay RW, usa RO (pero escribirá y fallará por permisos)
        url = get_db_url_ro()
    return url

def fetch_one(sql: str, params: tuple = (), *, rw: bool = False):
    with psycopg.connect(get_db_url_rw() if rw else get_db_url_ro()) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
        # commit si es RW (INSERT/UPDATE)
        if rw:
            conn.commit()
        return row

def fetch_all(sql: str, params: tuple = ()):
    with psycopg.connect(get_db_url_ro()) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(sql, params)
            return cur.fetchall()
