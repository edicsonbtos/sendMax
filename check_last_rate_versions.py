import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
db = os.getenv("DATABASE_URL")

with psycopg.connect(db) as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, kind, effective_from, reason
            FROM rate_versions
            ORDER BY id DESC
            LIMIT 10;
        """)
        rows = cur.fetchall()
        for r in rows:
            print(r)
