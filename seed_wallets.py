import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
db = os.getenv("DATABASE_URL")

with psycopg.connect(db) as conn:
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO wallets (user_id, balance_usdt)
            SELECT u.id, 0
            FROM users u
            WHERE NOT EXISTS (
                SELECT 1 FROM wallets w WHERE w.user_id = u.id
            );
        """)
        conn.commit()

        cur.execute("SELECT COUNT(*) FROM wallets;")
        print("wallets_count:", cur.fetchone()[0])
