import os
import psycopg
from dotenv import load_dotenv

from src.rates_generator import generate_rates_full

load_dotenv()
db = os.getenv("DATABASE_URL")

print("1) Generando baseline tipo auto_9am (test)...")
res = generate_rates_full(kind="auto_9am", reason="TEST baseline 9am (local)")
print("OK version_id:", res.version_id, "countries_ok:", len(res.countries_ok), "failed:", len(res.countries_failed), "any_unverified:", res.any_unverified)

print("\n2) Verificando DB (rate_versions, p2p_country_prices, route_rates) ...")
with psycopg.connect(db) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT id, kind, reason, effective_from FROM rate_versions WHERE id = %s;", (res.version_id,))
        print("rate_version:", cur.fetchone())

        cur.execute("SELECT COUNT(*) FROM p2p_country_prices WHERE rate_version_id = %s;", (res.version_id,))
        print("p2p_country_prices count:", cur.fetchone()[0])

        cur.execute("SELECT COUNT(*) FROM route_rates WHERE rate_version_id = %s;", (res.version_id,))
        print("route_rates count:", cur.fetchone()[0])

print("\nTEST COMPLETO ✅")
