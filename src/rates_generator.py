from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from itertools import product
import asyncio
import logging

from src.integrations.binance_p2p import BinanceP2PClient
from src.integrations.p2p_config import COUNTRIES
from src.db.connection import get_async_conn
from src.config.dynamic_settings import dynamic_config

logger = logging.getLogger(__name__)


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
    Genera una versión completa de tasas (STRICTLY ASYNC).
    ATÓMICO: toda la escritura a DB ocurre en una sola transacción.
    Si falla a mitad, se hace rollback y las tasas anteriores siguen activas.
    """
    client = BinanceP2PClient()
    try:
        now = datetime.now(timezone.utc)

        country_prices: dict[str, dict] = {}
        failed: list[str] = []
        any_unverified = False

        # Binance I/O (lectura externa, antes de la transacción)
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

        # Pre-fetch comisiones dinámicas desde DB (antes de la transacción)
        codes = sorted(country_prices.keys())
        commission_cache: dict[tuple[str, str], Decimal] = {}
        for origin, dest in product(codes, codes):
            if origin == dest:
                continue
            pct = await dynamic_config.get_commission_pct(origin, dest)
            commission_cache[(origin, dest)] = pct

        # === TRANSACCIÓN ATÓMICA ===
        # Todo lo que sigue ocurre en una sola transacción.
        # Si falla en cualquier punto, se hace rollback automático
        # y las tasas anteriores siguen activas.
        async with get_async_conn() as conn:
            async with conn.transaction():
                async with conn.cursor() as cur:
                    # 1. Desactivar versiones anteriores
                    await cur.execute(
                        "UPDATE rate_versions SET is_active = false WHERE is_active = true;"
                    )

                    # 2. Crear nueva versión
                    await cur.execute(
                        """
                        INSERT INTO rate_versions (kind, reason, effective_from, is_active)
                        VALUES (%s, %s, %s, true)
                        RETURNING id;
                        """,
                        (kind, reason, now),
                    )
                    res = await cur.fetchone()
                    version_id = int(res[0]) if res else 0

                    # 3. Guardar precios por país
                    for code, info in country_prices.items():
                        await cur.execute(
                            """
                            INSERT INTO p2p_country_prices (
                                rate_version_id, country, fiat,
                                buy_price, sell_price,
                                methods_used, amount_ref,
                                source, is_verified
                            )
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s);
                            """,
                            (
                                version_id,
                                code, info["fiat"],
                                info["buy"], info["sell"],
                                info["methods_used"], info["amount_ref"],
                                "binance_p2p", bool(info["is_verified"]),
                            ),
                        )

                    # 4. Guardar rutas (todas las combinaciones)
                    for origin, dest in product(codes, codes):
                        if origin == dest:
                            continue

                        buy_origin = country_prices[origin]["buy"]
                        sell_dest = country_prices[dest]["sell"]

                        pct = commission_cache[(origin, dest)]

                        rate_base = (sell_dest / buy_origin)
                        rate_client = rate_base * (Decimal("1.0") - pct)

                        await cur.execute(
                            """
                            INSERT INTO route_rates (
                                rate_version_id,
                                origin_country, dest_country,
                                commission_pct,
                                buy_origin, sell_dest,
                                rate_base, rate_client
                            )
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s);
                            """,
                            (
                                version_id,
                                origin, dest,
                                pct,
                                buy_origin, sell_dest,
                                rate_base, rate_client,
                            ),
                        )

                     # 5. === RUTAS VENEZUELA_CASH (Entrega en Efectivo) ===
                    # Fetch config outside inner loop (already in transaction, reads committed data)
                    cash_cfg = await dynamic_config.get_cash_delivery_config()
                    zelle_cost: Decimal = cash_cfg["zelle_usdt_cost"]       # e.g. 1.03
                    margin_zelle: Decimal = cash_cfg["margin_cash_zelle"]    # e.g. 0.12
                    margin_general: Decimal = cash_cfg["margin_cash_general"] # e.g. 0.10

                    for origin in codes:
                        try:
                            if origin == "USA":
                                # Costo fijo Zelle: 1.03 USD = 1 USDT
                                # el buy_origin=zelle_cost, sell_dest=1 (USD efectivo)
                                buy_origin_cash = zelle_cost
                                sell_dest_cash = Decimal("1")
                                rate_base_cash = sell_dest_cash / buy_origin_cash
                                rate_client_cash = rate_base_cash * (Decimal("1") - margin_zelle)
                                comm_pct_cash = margin_zelle
                            else:
                                # Costo de adquisición = precio de Binance BUY del país origen
                                buy_origin_cash = country_prices[origin]["buy"]
                                sell_dest_cash = Decimal("1")   # 1 USDT = 1 USD efectivo (delivery at par)
                                rate_base_cash = sell_dest_cash / buy_origin_cash
                                rate_client_cash = rate_base_cash * (Decimal("1") - margin_general)
                                comm_pct_cash = margin_general

                            await cur.execute(
                                """
                                INSERT INTO route_rates (
                                    rate_version_id,
                                    origin_country, dest_country,
                                    commission_pct,
                                    buy_origin, sell_dest,
                                    rate_base, rate_client
                                )
                                VALUES (%s,%s,%s,%s,%s,%s,%s,%s);
                                """,
                                (
                                    version_id,
                                    origin, "VENEZUELA_CASH",
                                    comm_pct_cash,
                                    buy_origin_cash, sell_dest_cash,
                                    rate_base_cash, rate_client_cash,
                                ),
                            )
                            logger.info(
                                "VENEZUELA_CASH route %s→CASH: buy_origin=%s rate_client=%s (margin=%s%%)",
                                origin, buy_origin_cash, rate_client_cash.quantize(Decimal("0.0001")),
                                (comm_pct_cash * 100).quantize(Decimal("0.01")),
                            )
                        except Exception as e:
                            logger.warning("Failed to generate VENEZUELA_CASH route for origin=%s: %s", origin, e)

        return GenerateResult(

            version_id=int(version_id),
            countries_ok=sorted(country_prices.keys()),
            countries_failed=failed,
            any_unverified=any_unverified,
        )

    finally:
        await client.close()
