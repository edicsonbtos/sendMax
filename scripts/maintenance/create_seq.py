import psycopg
from src.config.settings import settings

def main():
    with psycopg.connect(settings.DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE SEQUENCE IF NOT EXISTS orders_public_id_seq;")
            cur.execute(
                "SELECT setval('orders_public_id_seq', COALESCE((SELECT MAX(public_id) FROM orders), 0) + 1, false);"
            )
        conn.commit()
    print("OK: orders_public_id_seq creado y seteado")

if __name__ == "__main__":
    main()
