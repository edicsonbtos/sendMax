import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
db = os.getenv("DATABASE_URL")
if not db:
    raise RuntimeError("DATABASE_URL no está definido")

TARGET = "b71a73ee4d14"  # users

with psycopg.connect(db) as conn:
    with conn.cursor() as cur:
        cur.execute("UPDATE alembic_version SET version_num = %s;", (TARGET,))
        conn.commit()
        cur.execute("SELECT version_num FROM alembic_version;")
        print(cur.fetchall())
