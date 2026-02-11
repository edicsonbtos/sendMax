import os
import psycopg

url = os.environ["DATABASE_URL"]
with psycopg.connect(url) as conn:
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE varchar(64);")
    conn.commit()

print("OK: alembic_version.version_num -> varchar(64)")
