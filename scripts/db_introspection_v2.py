import psycopg
import json
import sys
import os

# Ensure imports from root work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

db_url = os.environ.get("DATABASE_URL")
if not db_url:
    print("Error: DATABASE_URL not set.")
    sys.exit(1)

results = {}

try:
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            # 1. Orders Status
            cur.execute("SELECT DISTINCT status FROM orders")
            results['orders_status'] = [r[0] for r in cur.fetchall()]
            
            # 2. Orders Columns
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'orders'")
            results['orders_cols'] = [r[0] for r in cur.fetchall()]
            
            # 3. Users Columns
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'users'")
            results['users_cols'] = [r[0] for r in cur.fetchall()]
            
            # 4. Withdrawals Columns
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'withdrawals'")
            results['withdrawals_cols'] = [r[0] for r in cur.fetchall()]
            
            # 5. Withdrawals Status
            cur.execute("SELECT DISTINCT status FROM withdrawals")
            results['withdrawals_status'] = [r[0] for r in cur.fetchall()]
            
            # 6. Wallet-related Tables
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_name LIKE '%wallet%' OR table_name LIKE '%origin%'")
            results['wallet_tables'] = [r[0] for r in cur.fetchall()]

    print(json.dumps(results, indent=2))
except Exception as e:
    print(f"Error: {e}")
