import os
import psycopg

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit("Missing DATABASE_URL env var")

with psycopg.connect(DATABASE_URL) as conn:
    with conn.cursor() as cur:
        cur.execute("select current_database(), current_schema();")
        print("DB/SCHEMA:", cur.fetchone())

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
        cols = cur.fetchall()
        print("\ncolumns for public.withdrawals:")
        for name, typ, notnull in cols:
            print(f"{name:28} {typ:25} notnull={notnull}")

        wanted = {"country","fiat","fiat_amount","reject_reason","resolved_at"}
        existing = {c[0] for c in cols}
        print("\nmissing expected columns:", sorted(list(wanted - existing)))

        cur.execute("""
            SELECT conname, pg_get_constraintdef(oid)
            FROM pg_constraint
            WHERE conrelid = 'public.withdrawals'::regclass
            ORDER BY conname;
        """)
        print("\nconstraints for public.withdrawals:")
        for name, defn in cur.fetchall():
            print(name, "=>", defn)
