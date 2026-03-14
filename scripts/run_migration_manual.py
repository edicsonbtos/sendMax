import psycopg
import os
import sys

# Ensure imports from root work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

db_url = os.environ.get("DATABASE_URL")
if not db_url:
    print("Error: DATABASE_URL not set.")
    sys.exit(1)

sql = """
CREATE TABLE IF NOT EXISTS daily_closures (
    id BIGSERIAL PRIMARY KEY,
    closure_date DATE NOT NULL UNIQUE,
    total_orders_count INTEGER NOT NULL DEFAULT 0,
    total_volume_origin NUMERIC(20, 2) NOT NULL DEFAULT 0,
    total_profit_usdt NUMERIC(20, 8) NOT NULL DEFAULT 0,
    total_profit_real NUMERIC(20, 8) NOT NULL DEFAULT 0,
    success_rate NUMERIC(5, 2) NOT NULL DEFAULT 100,
    best_operator_id BIGINT REFERENCES users(id),
    best_operator_alias VARCHAR(100),
    best_origin_country VARCHAR(50),
    best_dest_country VARCHAR(50),
    pending_withdrawals_count INTEGER NOT NULL DEFAULT 0,
    pending_withdrawals_amount NUMERIC(20, 8) NOT NULL DEFAULT 0,
    vaults_snapshot JSONB,
    wallet_balances_snapshot JSONB,
    warnings JSONB,
    notes TEXT,
    executed_by BIGINT REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_daily_closures_date ON daily_closures (closure_date);
"""

try:
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            conn.commit()
    print("SUCCESS: Table daily_closures created.")
except Exception as e:
    print(f"Error: {e}")
