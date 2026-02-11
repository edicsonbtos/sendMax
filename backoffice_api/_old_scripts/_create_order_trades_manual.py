import os
from dotenv import load_dotenv
import psycopg

load_dotenv()
url = os.getenv("DATABASE_URL")
assert url, "DATABASE_URL missing"

SQL = """
CREATE TABLE IF NOT EXISTS public.order_trades (
  id BIGSERIAL PRIMARY KEY,
  order_public_id BIGINT NOT NULL,
  side TEXT NOT NULL,
  fiat_currency TEXT NOT NULL,
  fiat_amount NUMERIC NOT NULL,
  price NUMERIC NULL,
  usdt_amount NUMERIC NOT NULL,
  fee_usdt NUMERIC NULL,
  source TEXT NULL,
  external_ref TEXT NULL,
  note TEXT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_by_user_id BIGINT NULL
);

CREATE INDEX IF NOT EXISTS ix_order_trades_order_public_id ON public.order_trades(order_public_id);
CREATE INDEX IF NOT EXISTS ix_order_trades_created_at ON public.order_trades(created_at);
CREATE INDEX IF NOT EXISTS ix_order_trades_side ON public.order_trades(side);
"""

with psycopg.connect(url) as conn:
    with conn.cursor() as cur:
        cur.execute(SQL)
    conn.commit()

print("order_trades created/verified")
