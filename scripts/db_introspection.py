import sys
import os
import json

# Add backoffice_api to path
sys.path.append(os.path.join(os.getcwd(), 'backoffice_api'))

from app.db import fetch_all

def audit():
    results = {}
    try:
        # 1. Orders Status
        res = fetch_all("SELECT DISTINCT status FROM orders")
        results['orders_status'] = [r['status'] for r in res]
        
        # 2. Orders Columns
        res = fetch_all("SELECT column_name FROM information_schema.columns WHERE table_name = 'orders'")
        results['orders_cols'] = [r['column_name'] for r in res]
        
        # 3. Users Columns
        res = fetch_all("SELECT column_name FROM information_schema.columns WHERE table_name = 'users'")
        results['users_cols'] = [r['column_name'] for r in res]
        
        # 4. Withdrawals Columns
        res = fetch_all("SELECT column_name FROM information_schema.columns WHERE table_name = 'withdrawals'")
        results['withdrawals_cols'] = [r['column_name'] for r in res]
        
        # 5. Withdrawals Status
        res = fetch_all("SELECT DISTINCT status FROM withdrawals")
        results['withdrawals_status'] = [r['status'] for r in res]
        
        # 6. Wallet-related Tables
        res = fetch_all("SELECT table_name FROM information_schema.tables WHERE table_name LIKE '%wallet%' OR table_name LIKE '%origin%'")
        results['wallet_tables'] = [r['table_name'] for r in res]

        print(json.dumps(results, indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    audit()
