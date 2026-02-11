import os
from dotenv import load_dotenv
import psycopg

load_dotenv()
url = os.getenv("DATABASE_URL")
assert url

with psycopg.connect(url) as conn:
    with conn.cursor() as cur:
        cur.execute("select count(*) from public.order_trades")
        print("order_trades count =", cur.fetchone()[0])
