import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
db = os.getenv("DATABASE_URL")

with psycopg.connect(db) as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT rate_version_id, COUNT(*)
            FROM route_rates
            GROUP BY rate_version_id
            ORDER BY rate_version_id;
        """)
        print(cur.fetchall())
