import psycopg
from src.config.settings import settings

def main():
    with psycopg.connect(settings.DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT schemaname, sequencename FROM pg_sequences WHERE sequencename ILIKE %s;", ("%orders%",))
            rows = cur.fetchall()
            print("Sequences que contienen 'orders':")
            print(rows)

            cur.execute("SELECT to_regclass(%s);", ("orders_public_id_seq",))
            print("to_regclass('orders_public_id_seq'):", cur.fetchone()[0])

            cur.execute("SELECT to_regclass(%s);", ("public.orders_public_id_seq",))
            print("to_regclass('public.orders_public_id_seq'):", cur.fetchone()[0])

if __name__ == "__main__":
    main()
