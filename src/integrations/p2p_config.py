"""
Configuración P2P por país.

Centraliza:
- código país interno (UPPERCASE)
- fiat
- métodos de pago en orden (fallback si el primero falla)
- transAmount de referencia

Esto permite agregar países sin tocar el motor.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CountryP2PConfig:
    country: str
    fiat: str
    buy_methods: list[str]
    sell_methods: list[str]
    trans_amount: float


COUNTRIES: dict[str, CountryP2PConfig] = {
    "USA": CountryP2PConfig(
        country="USA",
        fiat="USD",
        buy_methods=["Zelle"],
        sell_methods=["Zelle"],
        trans_amount=130,
    ),
    "CHILE": CountryP2PConfig(
        country="CHILE",
        fiat="CLP",
        buy_methods=["BancoEstado", "Santander"],
        sell_methods=["BancoEstado", "Santander"],
        trans_amount=95000,
    ),
    "PERU": CountryP2PConfig(
        country="PERU",
        fiat="PEN",
        buy_methods=["Yape", "BCP"],
        sell_methods=["Yape", "BCP"],
        trans_amount=150,
    ),
    "COLOMBIA": CountryP2PConfig(
        country="COLOMBIA",
        fiat="COP",
        buy_methods=["Nequi", "Bancolombia"],
        sell_methods=["Nequi", "Bancolombia"],
        trans_amount=150000,
    ),
    "VENEZUELA": CountryP2PConfig(
        country="VENEZUELA",
        fiat="VES",
        buy_methods=["PagoMovil", "Banesco", "TransferenciaBancaria"],
        sell_methods=["PagoMovil", "Banesco", "TransferenciaBancaria"],
        trans_amount=39000,
    ),
    "MEXICO": CountryP2PConfig(
        country="MEXICO",
        fiat="MXN",
        buy_methods=["BBVA", "OXXO"],
        sell_methods=["BBVA", "OXXO"],
        trans_amount=1500,
    ),
    "ARGENTINA": CountryP2PConfig(
        country="ARGENTINA",
        fiat="ARS",
        buy_methods=["MercadoPagoNew"],
        sell_methods=["MercadoPagoNew"],
        trans_amount=150000,
    ),
}