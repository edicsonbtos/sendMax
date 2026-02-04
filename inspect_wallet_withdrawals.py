import os
import psycopg
from urllib.parse import urlparse

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit("Missing DATABASE_URL env var")

def q(conn, sql, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchall()

def print_table(conn, table):
    print("\n=== TABLE:", table, "===")
    rows = q(conn, """
        SELECT
            c.column_name,
            c.data_type,
            c.udt_name,
            c.is_nullable
        FROM information_schema.columns c
        WHERE c.table_schema = 'public' AND c.table_name = %s
        ORDER BY c.ordinal_position;
    """, (table,))
    for r in rows:
        print(f"{r[0]:28} {r[1]:12} udt={r[2]:16} nullable={r[3]}")

def print_enum_values(conn, enum_udt_name):
    rows = q(conn, """
        SELECT e.enumlabel
        FROM pg_type t
        JOIN pg_enum e ON t.oid = e.enumtypid
        WHERE t.typname = %s
        ORDER BY e.enumsortorder;
    """, (enum_udt_name,))
    if rows:
        print("\nEnum values for", enum_udt_name, "=", [r[0] for r in rows])

with psycopg.connect(DATABASE_URL) as conn:
    print_table(conn, "withdrawals")
    # detect enum for withdrawals.status if any
    status_info = q(conn, """
        SELECT c.data_type, c.udt_name
        FROM information_schema.columns c
        WHERE c.table_schema='public' AND c.table_name='withdrawals' AND c.column_name='status'
        LIMIT 1;
    """)
    if status_info:
        data_type, udt_name = status_info[0]
        if data_type == "USER-DEFINED":
            print_enum_values(conn, udt_name)

    print_table(conn, "wallet_ledger")
