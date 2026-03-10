import psycopg
import json

db_url = 'postgresql://neondb_owner:npg_8Eqh0xcTGVXQ@ep-damp-wave-ahgz5qnw-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require'
results = {}

try:
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            # 1. Orders Status
            cur.execute("SELECT DISTINCT status FROM orders")
            results['orders_status'] = [r[0] for r in cur.fetchall()]
            
            # 2. Orders Columns
            cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'orders'")
            results['orders_cols'] = {r[0]: r[1] for r in cur.fetchall()}
            
            # 3. Users Columns
            cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'users'")
            results['users_cols'] = {r[0]: r[1] for r in cur.fetchall()}
            
            # 4. Withdrawals Columns
            cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'withdrawals'")
            results['withdrawals_cols'] = {r[0]: r[1] for r in cur.fetchall()}
            
            # 5. Withdrawals Status
            cur.execute("SELECT DISTINCT status FROM withdrawals")
            results['withdrawals_status'] = [r[0] for r in cur.fetchall()]
            
            # 6. Wallet-related Tables
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_name LIKE '%wallet%' OR table_name LIKE '%origin%'")
            results['wallet_tables'] = [r[0] for r in cur.fetchall()]

    with open('db_audit_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("DONE_AUDIT")
except Exception as e:
    print(f"Error: {e}")
