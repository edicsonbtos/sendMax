from src.integrations.binance_p2p import BinanceP2PClient

client = BinanceP2PClient()
try:
    q = client.fetch_first_verified_price(
        fiat="USD",
        trade_type="BUY",
        pay_methods=["Zelle"],
        trans_amount=130
    )
    print(q)
finally:
    client.close()
