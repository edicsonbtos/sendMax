import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL no está definido en .env")

TARGET = "7fd3eec5ddbb"

with psycopg.connect(DATABASE_URL) as conn:
    with conn.cursor() as cur:
        cur.execute("UPDATE alembic_version SET version_num = %s;", (TARGET,))
        conn.commit()
        cur.execute("SELECT version_num FROM alembic_version;")
        print(cur.fetchall())
