import os
from dotenv import load_dotenv
import psycopg

load_dotenv()
url = os.getenv("DATABASE_URL")
assert url, "DATABASE_URL missing"

with psycopg.connect(url) as conn:
    with conn.cursor() as cur:
        cur.execute(
            "select table_schema, table_name from information_schema.tables where table_name=%s",
            ("order_trades",),
        )
        print(cur.fetchall())
