from __future__ import annotations

"""
Generación de tasas (full) para Sendmax.

Este módulo sirve para 2 cosas:
1) Ejecutar manualmente: `python generate_rates_once.py`
2) Reutilizarse desde el bot-service (scheduler y botón admin) llamando:
   `generate_rates_full(kind=..., reason=...)`

Qué hace:
- Consulta precios BUY/SELL por país usando Binance P2P (con fallback de métodos).
- Crea una rate_version y la activa.
- Inserta p2p_country_prices.
- Calcula TODAS las rutas (origin != dest) y guarda route_rates.

Notas importantes:
- La comisión se toma desde `settings.commission_pct(origin, dest)` (configurable en .env).
- Si un país falla (no logra BUY o SELL), se omite para esa versión.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from src.config.settings import settings
from src.integrations.binance_p2p import BinanceP2PClient
from src.integrations.p2p_config import COUNTRIES, CountryP2PConfig
from src.db.repositories import rates_repo


def fetch_with_method_fallback(
    client: BinanceP2PClient,
    *,
    cfg: CountryP2PConfig,
    trade_type: str,
) -> Optional[tuple[Decimal, bool, str]]:
    """
    Intenta métodos en orden. Devuelve:
    - price (Decimal)
    - is_verified (bool) (del anuncio usado)
    - method_used (str)

    Si no se logra: None
    """
    methods = cfg.buy_methods if trade_type == "BUY" else cfg.sell_methods

    last_error = None
    for m in methods:
        try:
            q = client.fetch_first_price(
                fiat=cfg.fiat,
                trade_type=trade_type,
                pay_methods=[m],
                trans_amount=cfg.trans_amount,
            )
            return Decimal(str(q.price)), bool(q.is_verified), m
        except Exception as e:
            last_error = e
            continue

    print(f"[WARN] No se pudo obtener {trade_type} para {cfg.country} ({cfg.fiat}). Error: {last_error}")
    return None


def generate_rates_full(*, kind: str, reason: str) -> dict[str, object]:
    """
    Genera una versión completa de tasas y la activa.

    Retorna un dict con:
    - version_id
    - countries_ok
    - countries_failed
    - routes_inserted
    """
    client = BinanceP2PClient()
    try:
        now = datetime.now(timezone.utc)

        # 1) Consultar BUY/SELL por país (si falla un país, se omite)
        prices: dict[str, dict[str, object]] = {}
        failed_countries: list[str] = []

        for country, cfg in COUNTRIES.items():
            buy = fetch_with_method_fallback(client, cfg=cfg, trade_type="BUY")
            sell = fetch_with_method_fallback(client, cfg=cfg, trade_type="SELL")

            if not buy or not sell:
                failed_countries.append(country)
                continue

            buy_price, buy_verified, buy_method = buy
            sell_price, sell_verified, sell_method = sell

            prices[country] = {
                "fiat": cfg.fiat,
                "buy_price": buy_price,
                "sell_price": sell_price,
                # verificado conservador: true solo si BUY y SELL fueron verificados
                "is_verified": bool(buy_verified and sell_verified),
                "methods_used": f"BUY:{buy_method}|SELL:{sell_method}",
                "amount_ref": Decimal(str(cfg.trans_amount)),
            }

        if not prices:
            raise RuntimeError("No se pudo obtener precios de ningún país. Abortando versión.")

        # 2) Crear rate_version y activarla
        # Nota: dejamos una única versión activa a la vez.
        rates_repo.deactivate_all_rate_versions()
        version_id = rates_repo.create_rate_version(
            kind=kind,
            reason=reason,
            effective_from=now,
            is_active=True,
        )
        rates_repo.activate_rate_version(version_id)

        # 3) Guardar p2p_country_prices por país disponible
        for country, info in prices.items():
            rates_repo.insert_country_price(
                rate_version_id=version_id,
                country=country,
                fiat=str(info["fiat"]),
                buy_price=info["buy_price"],   # Decimal
                sell_price=info["sell_price"], # Decimal
                methods_used=str(info["methods_used"]),
                amount_ref=info["amount_ref"], # Decimal
                source="binance_p2p",
                is_verified=bool(info["is_verified"]),
            )

        # 4) Calcular TODAS las rutas (origin != dest) usando tasa_base y comisión
        countries_available = list(prices.keys())
        inserted_routes = 0

        for origin in countries_available:
            for dest in countries_available:
                if origin == dest:
                    continue

                buy_origin = prices[origin]["buy_price"]   # Decimal
                sell_dest = prices[dest]["sell_price"]     # Decimal

                # Comisión configurable por .env (Settings)
                com_pct = Decimal(str(settings.commission_pct(origin, dest)))

                rate_base = (sell_dest / buy_origin)
                rate_client = rate_base * (Decimal("1.0") - com_pct / Decimal("100.0"))

                rates_repo.insert_route_rate(
                    rate_version_id=version_id,
                    origin_country=origin,
                    dest_country=dest,
                    commission_pct=com_pct,
                    buy_origin=buy_origin,
                    sell_dest=sell_dest,
                    rate_base=rate_base,
                    rate_client=rate_client,
                )
                inserted_routes += 1

        return {
            "version_id": version_id,
            "countries_ok": countries_available,
            "countries_failed": failed_countries,
            "routes_inserted": inserted_routes,
        }

    finally:
        client.close()


def main() -> None:
    """
    CLI manual: genera una versión full y la activa.
    """
    res = generate_rates_full(
        kind="manual_full",
        reason="Manual full generation (all routes)",
    )
    print("OK. version_id =", res["version_id"])
    print("Countries OK:", res["countries_ok"])
    print("Countries FAILED:", res["countries_failed"])
    print("Routes inserted:", res["routes_inserted"])


if __name__ == "__main__":
    main()