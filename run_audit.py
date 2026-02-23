import asyncio
from src.db.connection import get_async_conn

async def run_diagnostics():
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            print("--- 3.1 Duplicados ledger ---")
            await cur.execute("""
                select user_id, type, ref_order_public_id, count(*) as n
                from wallet_ledger
                where ref_order_public_id is not null
                group by user_id, type, ref_order_public_id
                having count(*) > 1;
            """)
            rows = await cur.fetchall()
            for r in rows: print(r)
            if not rows: print("0 rows")

            print("\n--- 3.2 Awaiting_paid_proof en estados inválidos ---")
            await cur.execute("""
                select public_id, status, awaiting_paid_proof, awaiting_paid_proof_at
                from orders
                where awaiting_paid_proof = true
                  and status not in ('EN_PROCESO','ORIGEN_CONFIRMADO');
            """)
            rows = await cur.fetchall()
            for r in rows: print(r)
            if not rows: print("0 rows")

            print("\n--- 3.3 Duplicados origin_receipts_ledger ---")
            # Try to catch if the table doesn't exist yet (before migration)
            try:
                await cur.execute("""
                    select ref_order_public_id, count(*) as n
                    from origin_receipts_ledger
                    group by ref_order_public_id
                    having count(*) > 1;
                """)
                rows = await cur.fetchall()
                for r in rows: print(r)
                if not rows: print("0 rows")
            except Exception as e:
                print(f"Table maybe not created yet: {e}")

            print("\n--- 3.4 Confirmar índice parcial realmente creado ---")
            await cur.execute("""
                select indexname, indexdef
                from pg_indexes
                where tablename='wallet_ledger' and indexname = 'ux_wallet_ledger_idempotency';
            """)
            rows = await cur.fetchall()
            for r in rows: print(r)
            if not rows: print("0 rows (run migrations first)")

if __name__ == "__main__":
    asyncio.run(run_diagnostics())
