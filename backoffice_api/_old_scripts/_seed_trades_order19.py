import os
from dotenv import load_dotenv
import psycopg

load_dotenv()
url = os.getenv("DATABASE_URL")
assert url

ORDER_PUBLIC_ID = 19

BUY = dict(
    order_public_id=ORDER_PUBLIC_ID,
    side="BUY",
    fiat_currency="VES",
    fiat_amount=6200,
    price=550.0,
    usdt_amount=11.27,
    fee_usdt=0.0,
    source="binance",
    external_ref="",
    note="Compra en Binance",
)

SELL = dict(
    order_public_id=ORDER_PUBLIC_ID,
    side="SELL",
    fiat_currency="ARS",
    fiat_amount=15320,
    price=1466.0,
    usdt_amount=10.45,
    fee_usdt=0.0,
    source="binance",
    external_ref="",
    note="Venta en Binance",
)

INS = """
INSERT INTO public.order_trades
(order_public_id, side, fiat_currency, fiat_amount, price, usdt_amount, fee_usdt, source, external_ref, note)
VALUES (%(order_public_id)s, %(side)s, %(fiat_currency)s, %(fiat_amount)s, %(price)s, %(usdt_amount)s, %(fee_usdt)s, %(source)s, %(external_ref)s, %(note)s)
RETURNING id
"""

with psycopg.connect(url) as conn:
    with conn.cursor() as cur:
        cur.execute(INS, BUY)
        buy_id = cur.fetchone()[0]
        cur.execute(INS, SELL)
        sell_id = cur.fetchone()[0]

        conn.commit()

        cur.execute(
            "select id, side, fiat_currency, fiat_amount, price, usdt_amount, fee_usdt, created_at from public.order_trades where order_public_id=%s order by id asc",
            (ORDER_PUBLIC_ID,),
        )
        rows = cur.fetchall()

print("Inserted BUY id=", buy_id, "SELL id=", sell_id)
print("Trades:", rows)
