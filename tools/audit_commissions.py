import psycopg
from decimal import Decimal
from src.config.settings import settings

def q2(x: Decimal) -> str:
    return str(x.quantize(Decimal("0.01")))

def main():
    with psycopg.connect(settings.DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT public_id, operator_user_id, profit_usdt
                FROM orders
                WHERE status='PAGADA' AND profit_usdt IS NOT NULL
                ORDER BY public_id DESC
                LIMIT 10;
            """)
            orders = cur.fetchall()

            print("public_id | operator_user_id | profit_usdt | op_ledger_sum | sponsor_ledger_sum | op_pct | sponsor_pct")

            for pid, op_uid, profit in orders:
                profit = Decimal(str(profit))

                cur.execute("""
                    SELECT COALESCE(SUM(amount_usdt),0)
                    FROM wallet_ledger
                    WHERE ref_order_public_id=%s
                      AND user_id=%s
                      AND type='ORDER_PROFIT';
                """, (pid, op_uid))
                op_sum = Decimal(str(cur.fetchone()[0]))

                cur.execute("""
                    SELECT COALESCE(SUM(amount_usdt),0)
                    FROM wallet_ledger
                    WHERE ref_order_public_id=%s
                      AND type='SPONSOR_COMMISSION';
                """, (pid,))
                sp_sum = Decimal(str(cur.fetchone()[0]))

                if profit != 0:
                    op_pct = (op_sum / profit) * Decimal("100")
                    sp_pct = (sp_sum / profit) * Decimal("100")
                else:
                    op_pct = Decimal("0")
                    sp_pct = Decimal("0")

                print(f"{pid} | {op_uid} | {profit} | {op_sum} | {sp_sum} | {q2(op_pct)}% | {q2(sp_pct)}%")

if __name__ == "__main__":
    main()
