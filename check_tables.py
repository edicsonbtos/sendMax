import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
db = os.getenv("DATABASE_URL")
if not db:
    raise RuntimeError("DATABASE_URL no está definido")

with psycopg.connect(db) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;")
        rows = cur.fetchall()
        print([r[0] for r in rows])
