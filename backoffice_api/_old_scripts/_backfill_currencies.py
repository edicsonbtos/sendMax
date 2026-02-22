import os
from dotenv import load_dotenv
import psycopg

load_dotenv()
url = os.getenv("DATABASE_URL")
assert url, "DATABASE_URL missing"

SQL1 = """
UPDATE orders
SET origin_currency = CASE upper(origin_country)
  WHEN 'CHILE' THEN 'CLP'
  WHEN 'PERU' THEN 'PEN'
  WHEN 'USA' THEN 'USD'
  WHEN 'VENEZUELA' THEN 'VES'
  WHEN 'VE' THEN 'VES'
  WHEN 'COLOMBIA' THEN 'COP'
  WHEN 'ARGENTINA' THEN 'ARS'
  WHEN 'MEXICO' THEN 'MXN'
  ELSE origin_currency
END
WHERE origin_currency IS NULL
"""

SQL2 = """
UPDATE orders
SET dest_currency = CASE upper(dest_country)
  WHEN 'CHILE' THEN 'CLP'
  WHEN 'PERU' THEN 'PEN'
  WHEN 'USA' THEN 'USD'
  WHEN 'VENEZUELA' THEN 'VES'
  WHEN 'VE' THEN 'VES'
  WHEN 'COLOMBIA' THEN 'COP'
  WHEN 'ARGENTINA' THEN 'ARS'
  WHEN 'MEXICO' THEN 'MXN'
  ELSE dest_currency
END
WHERE dest_currency IS NULL
"""

with psycopg.connect(url) as conn:
    with conn.cursor() as cur:
        cur.execute(SQL1)
        cur.execute(SQL2)
        conn.commit()

        cur.execute("select origin_currency, count(*) cnt from orders group by 1 order by cnt desc")
        print("origin_currency counts=", cur.fetchall())

        cur.execute("select dest_currency, count(*) cnt from orders group by 1 order by cnt desc")
        print("dest_currency counts=", cur.fetchall())
