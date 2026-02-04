from src.integrations.binance_p2p import BinanceP2PClient

client = BinanceP2PClient()
try:
    buy_q = client.fetch_first_price(
        fiat="USD",
        trade_type="BUY",
        pay_methods=["Zelle"],
        trans_amount=130
    )
    sell_q = client.fetch_first_price(
        fiat="USD",
        trade_type="SELL",
        pay_methods=["Zelle"],
        trans_amount=130
    )
    print("BUY :", buy_q)
    print("SELL:", sell_q)
finally:
    client.close()
