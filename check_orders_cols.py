import os, psycopg
from dotenv import load_dotenv

load_dotenv()
db = os.getenv("DATABASE_URL")

with psycopg.connect(db) as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema='public' AND table_name='orders'
            ORDER BY ordinal_position;
        """)
        cols = [r[0] for r in cur.fetchall()]
        print("cancel_reason" in cols, cols)
