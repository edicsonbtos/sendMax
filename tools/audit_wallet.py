import psycopg
from src.config.settings import settings

def main():
    with psycopg.connect(settings.DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT public_id, status, profit_usdt, paid_at FROM orders ORDER BY public_id DESC LIMIT 5;")
            orders = cur.fetchall()

            cur.execute("SELECT id, user_id, amount_usdt, status, country, fiat, fiat_amount, created_at FROM withdrawals ORDER BY id DESC LIMIT 5;")
            withdrawals = cur.fetchall()

            cur.execute("SELECT user_id, balance_usdt, updated_at FROM wallets ORDER BY updated_at DESC LIMIT 5;")
            wallets = cur.fetchall()

            cur.execute("SELECT id, user_id, amount_usdt, type, memo, created_at FROM wallet_ledger ORDER BY id DESC LIMIT 10;")
            ledger = cur.fetchall()

    print("--- last orders ---")
    for r in orders:
        print(r)

    print("\n--- last withdrawals ---")
    for r in withdrawals:
        print(r)

    print("\n--- last wallets ---")
    for r in wallets:
        print(r)

    print("\n--- last ledger ---")
    for r in ledger:
        print(r)

if __name__ == "__main__":
    main()
