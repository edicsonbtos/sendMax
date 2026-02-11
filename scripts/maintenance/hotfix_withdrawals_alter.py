import os
import psycopg

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit("Missing DATABASE_URL env var")

cols = [
    ("country", "text"),
    ("fiat", "text"),
    ("fiat_amount", "numeric(18,2)"),
    ("reject_reason", "text"),
    ("resolved_at", "timestamptz"),
]

with psycopg.connect(DATABASE_URL) as conn:
    with conn.cursor() as cur:
        for name, typ in cols:
            cur.execute(f'ALTER TABLE public.withdrawals ADD COLUMN IF NOT EXISTS {name} {typ};')
        conn.commit()

print("OK: columns ensured on public.withdrawals")
