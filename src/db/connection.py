import logging
import psycopg
from src.config.settings import settings

logger = logging.getLogger("db")

def ping_db() -> bool:
    try:
        with psycopg.connect(settings.DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
        return True
    except Exception as e:
        logger.exception("DB ping failed: %s", e)
        return False