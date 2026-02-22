import os
from dotenv import load_dotenv
import psycopg

load_dotenv()

url = os.getenv("DATABASE_URL") or os.getenv("DATABASE_URL_RW") or os.getenv("DATABASE_URL_RO")
assert url, "No DATABASE_URL/DATABASE_URL_RW/DATABASE_URL_RO"

with psycopg.connect(url) as conn:
    with conn.cursor() as cur:
        cur.execute(
            "select column_name from information_schema.columns where table_schema=%s and table_name=%s and column_name=%s",
            ("public", "orders", "profit_real_usdt"),
        )
        print("column=", cur.fetchall())

        cur.execute("select current_user")
        print("db_user=", cur.fetchone())
