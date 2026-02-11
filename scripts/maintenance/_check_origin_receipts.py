import os, psycopg
url = os.environ["DATABASE_URL"]
with psycopg.connect(url) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT day, origin_country, fiat_currency, amount_fiat FROM origin_receipts_daily ORDER BY day, origin_country;")
        for r in cur.fetchall():
            print(r)
