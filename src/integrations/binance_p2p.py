from __future__ import annotations

import httpx
from dataclasses import dataclass
from typing import Iterable
from src.db.settings_store import get_setting_float

BINANCE_P2P_URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"

@dataclass(frozen=True)
class P2PQuote:
    trade_type: str          # "BUY" or "SELL"
    fiat: str                # "USD", "VES", etc.
    price: float             # fiat per 1 USDT
    method: str              # payment method used
    advertiser_nick: str | None
    is_verified: bool

class BinanceP2PClient:
    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self._client = httpx.AsyncClient(timeout=timeout_seconds)

    async def close(self) -> None:
        await self._client.aclose()

    async def fetch_first_price(
        self,
        *,
        fiat: str,
        trade_type: str,
        pay_methods: Iterable[str],
        trans_amount: float,
        asset: str = "USDT",
    ) -> P2PQuote:
        pay_types = list(pay_methods)

        # AWAIT is mandatory here
        rows_val = await get_setting_float("p2p_rows", "rows", 10.0)

        payload = {
            "page": 1,
            "rows": int(rows_val),
            "payTypes": pay_types,
            "asset": asset,
            "fiat": fiat,
            "tradeType": trade_type,
            "transAmount": str(trans_amount),
            "publisherType": None,
        }

        headers = {
            "content-type": "application/json",
            "accept": "*/*",
            "user-agent": "sendmax-bot/1.0",
        }

        try:
            resp = await self._client.post(BINANCE_P2P_URL, json=payload, headers=headers)
            resp.raise_for_status()
        except httpx.TimeoutException:
            raise RuntimeError(f"Timeout consulting Binance P2P ({fiat}/{trade_type}).")
        except Exception as e:
            raise RuntimeError(f"Network error consulting Binance P2P: {e}")

        data = resp.json()
        items = data.get("data") or []
        if not items:
            raise RuntimeError(f"No P2P ads for fiat={fiat} tradeType={trade_type} methods={pay_types}")

        method_used = pay_types[0] if pay_types else "UNKNOWN"

        def to_quote(item, verified: bool) -> P2PQuote:
            advertiser = item.get("advertiser") or {}
            adv = item.get("adv") or {}
            price_str = adv.get("price")
            if price_str is None:
                raise RuntimeError("Binance response missing 'adv.price'")
            return P2PQuote(
                trade_type=trade_type,
                fiat=fiat,
                price=float(price_str),
                method=method_used,
                advertiser_nick=advertiser.get("nickName"),
                is_verified=verified,
            )

        for item in items:
            advertiser = item.get("advertiser") or {}
            is_v = bool(advertiser.get("isVerified")) or (advertiser.get("userType") == "merchant")
            if is_v:
                return to_quote(item, verified=True)

        return to_quote(items[0], verified=False)
