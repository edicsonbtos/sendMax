import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
try:
    url = os.getenv("DATABASE_URL")
    if not url:
        print("Error: No se encontró DATABASE_URL en .env")
    else:
        with psycopg.connect(url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT tablename FROM pg_tables WHERE tablename IN ('wallets','wallet_ledger','withdrawals')")
                rows = cur.fetchall()
                print("Tablas encontradas:", [r[0] for r in rows])
except Exception as e:
    print("Error conectando a DB:", e)
