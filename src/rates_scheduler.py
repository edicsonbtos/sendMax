"""
Scheduler de tasas usando JobQueue de python-telegram-bot.

- run_9am_baseline: genera tasas completas a las 9am VET
- run_30m_check: compara precios actuales de Binance con la última versión
  y regenera si la variación supera el umbral configurado (default 3%).
"""
from __future__ import annotations

import logging
from decimal import Decimal

logger = logging.getLogger("rates_scheduler")


class RatesScheduler:
    def __init__(self, app):
        self.app = app

    async def run_9am_baseline(self) -> None:
        """Genera tasas completas (baseline diario)."""
        logger.info("[rates] 9am baseline job — generando tasas …")
        try:
            from src.rates_generator import generate_rates_full

            res = await generate_rates_full(
                kind="auto_9am",
                reason="Baseline diario 9am",
            )
            logger.info(
                "[rates] 9am OK — version=%s  ok=%s  failed=%s",
                res.version_id,
                res.countries_ok,
                res.countries_failed,
            )
        except Exception:
            logger.exception("[rates] 9am baseline FALLÓ (se reintentará en 30 min)")

    async def run_30m_check(self) -> None:
        """
        Compara precios actuales de Binance con los guardados.
        Si algún país varía más del umbral, regenera tasas.
        """
        logger.info("[rates] 30m check — comparando precios …")
        try:
            from src.db.settings_store import get_setting_float
            from src.db.repositories.rates_repo import (
                get_latest_active_rate_version,
                get_country_price_for_version,
            )
            from src.integrations.binance_p2p import BinanceP2PClient
            from src.integrations.p2p_config import COUNTRIES

            # Umbral configurable desde DB (default 3%)
            threshold = await get_setting_float(
                "price_variation_threshold", "percent", 3.0
            )
            threshold_pct = Decimal(str(threshold)) / Decimal("100")

            rv = await get_latest_active_rate_version()
            if not rv:
                logger.warning("[rates] 30m check — no hay versión activa, generando …")
                await self.run_9am_baseline()
                return

            client = BinanceP2PClient()
            try:
                needs_regen = False

                for code, cfg in COUNTRIES.items():
                    cp = await get_country_price_for_version(
                        rate_version_id=rv.id, country=code
                    )
                    if not cp:
                        continue

                    try:
                        buy_quote = await client.fetch_first_price(
                            fiat=cfg.fiat,
                            trade_type="BUY",
                            pay_methods=cfg.buy_methods,
                            trans_amount=cfg.trans_amount,
                        )
                        current_buy = Decimal(str(buy_quote.price))
                        saved_buy = Decimal(str(cp.buy_price))

                        if saved_buy > 0:
                            var = abs(current_buy - saved_buy) / saved_buy
                            if var >= threshold_pct:
                                logger.info(
                                    "[rates] %s BUY varió %.2f%% (umbral %.2f%%) — regenerando",
                                    code,
                                    float(var * 100),
                                    float(threshold_pct * 100),
                                )
                                needs_regen = True
                                break
                    except Exception as e:
                        logger.warning("[rates] 30m check error para %s: %s", code, e)
                        continue

                if needs_regen:
                    from src.rates_generator import generate_rates_full

                    res = await generate_rates_full(
                        kind="auto_30m",
                        reason=f"Variación detectada >{threshold}%",
                    )
                    logger.info(
                        "[rates] 30m regen OK — version=%s",
                        res.version_id,
                    )
                else:
                    logger.info("[rates] 30m check — sin variación significativa")

            finally:
                await client.close()

        except Exception:
            logger.exception("[rates] 30m check FALLÓ")