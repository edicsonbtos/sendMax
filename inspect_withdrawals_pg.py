import os
import psycopg

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit("Missing DATABASE_URL env var")

with psycopg.connect(DATABASE_URL) as conn:
    with conn.cursor() as cur:
        cur.execute("select current_database(), current_schema();")
        print("DB/SCHEMA:", cur.fetchone())

        # columns (pg_catalog is authoritative)
        cur.execute("""
            SELECT a.attname, pg_catalog.format_type(a.atttypid, a.atttypmod) AS type,
                   a.attnotnull
            FROM pg_attribute a
            JOIN pg_class c ON c.oid = a.attrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname='public' AND c.relname='withdrawals'
              AND a.attnum > 0 AND NOT a.attisdropped
            ORDER BY a.attnum;
        """)
        print("\npg_attribute columns for public.withdrawals:")
        for name, typ, notnull in cur.fetchall():
            print(f"{name:28} {typ:25} notnull={notnull}")

        # show table definition using pg_get_tabledef-ish via pg_dump style
        cur.execute("""
            SELECT pg_get_tabledef('public.withdrawals'::regclass);
        """)
        print("\npg_get_tabledef(public.withdrawals):\n", cur.fetchone()[0])
