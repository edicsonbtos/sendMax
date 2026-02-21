from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from itertools import product
import asyncio

from src.integrations.binance_p2p import BinanceP2PClient
from src.integrations.p2p_config import COUNTRIES
from src.db.repositories import rates_repo
from src.db.settings_store import get_setting_float
from src.config.settings import settings


@dataclass(frozen=True)
class GenerateResult:
    version_id: int
    countries_ok: list[str]
    countries_failed: list[str]
    any_unverified: bool


async def _pick_price_with_method_fallback(client: BinanceP2PClient, *, fiat: str, trade_type: str, methods: list[str], trans_amount: float):
    last_err = None
    for m in methods:
        try:
            q = await client.fetch_first_price(
                fiat=fiat,
                trade_type=trade_type,
                pay_methods=[m],
                trans_amount=trans_amount,
            )
            return (Decimal(str(q.price)), bool(q.is_verified), m)
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"No se pudo obtener {trade_type} para fiat={fiat} methods={methods}. Last={last_err}")


async def generate_rates_full(*, kind: str, reason: str) -> GenerateResult:
    """
    Genera una version completa de tasas (STRICTLY ASYNC).
    """
    client = BinanceP2PClient()
    try:
        now = datetime.now(timezone.utc)

        # Pre-fetch configuración desde DB (una sola vez)
        m_default = await get_setting_float("margin_default", "percent", settings.COMMISSION_DEFAULT)
        m_venez = await get_setting_float("margin_dest_venez", "percent", settings.COMMISSION_VENEZUELA)
        m_usa_venez = await get_setting_float("margin_route_usa_venez", "percent", settings.COMMISSION_USA_TO_VENEZUELA)

        country_prices: dict[str, dict] = {}
        failed: list[str] = []
        any_unverified = False

        # Binance I/O ahora es asíncrono
        for code, cfg in COUNTRIES.items():
            try:
                buy_price, buy_verified, buy_method = await _pick_price_with_method_fallback(
                    client, fiat=cfg.fiat, trade_type="BUY", methods=cfg.buy_methods, trans_amount=cfg.trans_amount
                )
                sell_price, sell_verified, sell_method = await _pick_price_with_method_fallback(
                    client, fiat=cfg.fiat, trade_type="SELL", methods=cfg.sell_methods, trans_amount=cfg.trans_amount
                )

                is_verified = bool(buy_verified and sell_verified)
                if not is_verified:
                    any_unverified = True

                country_prices[code] = {
                    "fiat": cfg.fiat,
                    "buy": buy_price,
                    "sell": sell_price,
                    "is_verified": is_verified,
                    "methods_used": f"BUY:{buy_method}|SELL:{sell_method}",
                    "amount_ref": Decimal(str(cfg.trans_amount)),
                }
            except Exception:
                failed.append(code)

        if len(country_prices) < 2:
            raise RuntimeError("No hay suficientes paises con precios para generar rutas (>=2).")

        # Crear version activa (DB async)
        await rates_repo.deactivate_all_rate_versions()
        version_id = await rates_repo.create_rate_version(
            kind=kind,
            reason=reason,
            effective_from=now,
            is_active=True,
        )
        await rates_repo.activate_rate_version(version_id)

        # Guardar precios pais
        for code, info in country_prices.items():
            await rates_repo.insert_country_price(
                rate_version_id=version_id,
                country=code,
                fiat=info["fiat"],
                buy_price=info["buy"],
                sell_price=info["sell"],
                methods_used=info["methods_used"],
                amount_ref=info["amount_ref"],
                source="binance_p2p",
                is_verified=bool(info["is_verified"]),
            )

        # Guardar rutas (todas combinaciones)
        codes = sorted(country_prices.keys())
        for origin, dest in product(codes, codes):
            if origin == dest:
                continue

            buy_origin = country_prices[origin]["buy"]
            sell_dest = country_prices[dest]["sell"]

            # Usamos los márgenes resueltos arriba
            pct_val = settings.commission_pct(
                origin, dest,
                override_default=m_default,
                override_venez=m_venez,
                override_usa_venez=m_usa_venez
            )
            pct = Decimal(str(pct_val))

            rate_base = (sell_dest / buy_origin)
            rate_client = rate_base * (Decimal("1.0") - pct)

            await rates_repo.insert_route_rate(
                rate_version_id=version_id,
                origin_country=origin,
                dest_country=dest,
                commission_pct=pct,
                buy_origin=buy_origin,
                sell_dest=sell_dest,
                rate_base=rate_base,
                rate_client=rate_client,
            )

        return GenerateResult(
            version_id=int(version_id),
            countries_ok=sorted(country_prices.keys()),
            countries_failed=failed,
            any_unverified=any_unverified,
        )

    finally:
        await client.close()
