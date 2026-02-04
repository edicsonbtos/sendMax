import os
from decimal import Decimal
import psycopg
from src.config.settings import settings

def main():
    public_id = input("public_id de la orden: ").strip()
    if not public_id.isdigit():
        raise SystemExit("public_id inválido")

    pid = int(public_id)

    sql_ledger = """
    SELECT id, user_id, amount_usdt, type, ref_order_public_id, memo, created_at
    FROM wallet_ledger
    WHERE ref_order_public_id = %s
    ORDER BY id ASC;
    """

    sql_wallets = """
    SELECT user_id, balance_usdt, updated_at
    FROM wallets
    WHERE user_id IN (
      (SELECT operator_user_id FROM orders WHERE public_id = %s),
      (SELECT sponsor_id FROM users WHERE id = (SELECT operator_user_id FROM orders WHERE public_id = %s))
    )
    ORDER BY user_id;
    """

    with psycopg.connect(settings.DATABASE_URL) as conn:
        with conn.cursor() as cur:
            print("\n--- wallet_ledger for order ---")
            cur.execute(sql_ledger, (pid,))
            rows = cur.fetchall()
            if not rows:
                print("(sin filas)")
            else:
                for r in rows:
                    print(r)

            print("\n--- wallets for operator/sponsor ---")
            cur.execute(sql_wallets, (pid, pid))
            rows = cur.fetchall()
            if not rows:
                print("(sin filas)")
            else:
                for r in rows:
                    print(r)

if __name__ == "__main__":
    main()
