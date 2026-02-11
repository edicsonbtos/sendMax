import httpx

url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"

payload = {
    "page": 1,
    "rows": 5,
    "payTypes": [],
    "asset": "USDT",
    "fiat": "ARS",
    "tradeType": "BUY",
    "transAmount": "150000",
}

r = httpx.post(url, json=payload, timeout=20)
print("status:", r.status_code)
data = r.json()
print("items:", len(data.get("data") or []))
if data.get("data"):
    first = data["data"][0]
    adv = first.get("adv") or {}
    advertiser = first.get("advertiser") or {}
    print("first_price:", adv.get("price"))
    print("first_methods:", [m.get("identifier") for m in (adv.get("tradeMethods") or [])][:10])
    print("advertiser_userType:", advertiser.get("userType"))
    print("advertiser_isVerified:", advertiser.get("isVerified"))
