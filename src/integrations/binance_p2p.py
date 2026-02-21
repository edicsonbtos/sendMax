"""
Cliente simple para Binance P2P (endpoint público).

Objetivo:
- Consultar precio BUY y SELL de USDT por país (fiat)
- Preferir merchant verificado; si no existe, fallback al primer anuncio
- NO requiere API KEY (endpoint público)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import httpx

from src.db.settings_store import get_setting_float

BINANCE_P2P_URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"


@dataclass(frozen=True)
class P2PQuote:
    trade_type: str          # "BUY" or "SELL"
    fiat: str                # "USD", "VES", etc.
    price: float             # fiat per 1 USDT
    method: str              # payment method used (primer método pedido)
    advertiser_nick: str | None
    is_verified: bool        # trazabilidad


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
        """
        Devuelve un precio P2P (ASYNC).
        Política:
        1) si hay anuncios de merchant verificado, toma el primero verificado
        2) si no hay verificados, toma el primer anuncio disponible (fallback)
        """

        pay_types = list(pay_methods)

        # Configuración dinámica desde DB
        p2p_rows = await get_setting_float("p2p_rows", "rows", 10.0)

        payload = {
            "page": 1,
            "rows": int(p2p_rows),
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
            raise RuntimeError(f"Tiempo de espera agotado al consultar Binance P2P ({fiat}/{trade_type}).")
        except Exception as e:
            raise RuntimeError(f"Error de red al consultar Binance P2P: {e}")

        data = resp.json()
        items = data.get("data") or []
        if not items:
            raise RuntimeError(
                f"No hay anuncios P2P para fiat={fiat} tradeType={trade_type} methods={pay_types}"
            )

        method_used = pay_types[0] if pay_types else "UNKNOWN"

        def to_quote(item, verified: bool) -> P2PQuote:
            advertiser = (item.get("advertiser") or {})
            adv = (item.get("adv") or {})
            price_str = adv.get("price")
            if price_str is None:
                raise RuntimeError("Respuesta Binance sin 'adv.price'")

            return P2PQuote(
                trade_type=trade_type,
                fiat=fiat,
                price=float(price_str),
                method=method_used,
                advertiser_nick=advertiser.get("nickName"),
                is_verified=verified,
            )

        # 1) buscar verificado
        for item in items:
            advertiser = (item.get("advertiser") or {})
            is_verified = bool(advertiser.get("isVerified")) or (advertiser.get("userType") == "merchant")
            if is_verified:
                return to_quote(item, verified=True)

        # 2) fallback: primer anuncio
        return to_quote(items[0], verified=False)