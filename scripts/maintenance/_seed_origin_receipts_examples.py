import os, psycopg
url = os.environ["DATABASE_URL"]

rows = [
    ("2026-03-01", "CHILE", "CLP", "100000"),
    ("2026-03-01", "PERU",  "PEN", "500"),
]

with psycopg.connect(url) as conn:
    with conn.cursor() as cur:
        for day, country, curcy, amt in rows:
            cur.execute(
                """
                INSERT INTO origin_receipts_daily(day, origin_country, fiat_currency, amount_fiat, note)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (day, origin_country, fiat_currency)
                DO UPDATE SET amount_fiat = EXCLUDED.amount_fiat
                """,
                (day, country, curcy, amt, "seed example")
            )
    conn.commit()

print("OK inserted/updated examples")
