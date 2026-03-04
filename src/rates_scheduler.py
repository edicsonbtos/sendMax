"""
Scheduler de tasas usando JobQueue de python-telegram-bot.

- run_9am_baseline: genera tasas completas a las 9am VET
- run_30m_check: compara precios actuales de Binance con la última versión
  y regenera si la variación supera el umbral configurado (default 3%).

Sprint 4 (Alert Copilot):
- run_vault_alert_check: alerta si vault.balance < vault.alert_threshold
- run_stuck_orders_check: alerta si orden lleva > 2h en estado activo sin cerrar
"""
from __future__ import annotations

import logging
from decimal import Decimal

from src.config.settings import settings
from src.db.connection import get_async_conn

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
                        from src.integrations.price_override import get_buy_price
                        current_buy = await get_buy_price(code, cfg.buy_methods[0])
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

    # ════════════════════════════════════════════════════════════
    # SPRINT 4 — Copiloto de Alertas
    # ════════════════════════════════════════════════════════════

    async def run_vault_alert_check(self) -> None:
        """Alerta si alguna bóveda tiene balance < alert_threshold."""
        admin_chat_id = getattr(settings, "ADMIN_TELEGRAM_USER_ID", None)
        if not admin_chat_id:
            logger.warning("[vault_alert] ADMIN_TELEGRAM_USER_ID no configurado")
            return
        try:
            async with get_async_conn() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        SELECT name, balance, alert_threshold, type
                        FROM vaults
                        WHERE is_active = true
                          AND alert_threshold > 0
                          AND balance < alert_threshold
                        ORDER BY (alert_threshold - balance) DESC;
                        """
                    )
                    cols = [d[0] for d in cur.description]
                    rows = await cur.fetchall()

            if not rows:
                logger.info("[vault_alert] Todas las bóvedas OK")
                return

            lines = ["🚨 <b>RADAR DE BÓVEDAS — STOCK BAJO</b>\n"]
            for row in rows:
                r = dict(zip(cols, row))
                deficit = float(r["alert_threshold"]) - float(r["balance"])
                lines.append(
                    f"⚠️ <b>{r['name']}</b>  [{r.get('type', '?')}]\n"
                    f"   Saldo: <b>${float(r['balance']):.2f}</b> "
                    f"/ Mínimo: ${float(r['alert_threshold']):.2f} "
                    f"(déficit: <b>-${deficit:.2f}</b>)"
                )

            await self.app.bot.send_message(
                chat_id=int(admin_chat_id),
                text="\n\n".join(lines),
                parse_mode="HTML",
            )
            logger.info("[vault_alert] Alerta enviada: %d bóvedas bajo mínimo", len(rows))

        except Exception:
            logger.exception("[vault_alert] Error en run_vault_alert_check")

    async def run_stuck_orders_check(self) -> None:
        """Alerta si alguna orden lleva más de 2h sin moverse."""
        admin_chat_id = getattr(settings, "ADMIN_TELEGRAM_USER_ID", None)
        if not admin_chat_id:
            return
        try:
            async with get_async_conn() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        SELECT public_id, status, origin_country, dest_country,
                               amount_origin,
                               EXTRACT(EPOCH FROM (now() - updated_at)) / 3600 AS hours_stuck
                        FROM orders
                        WHERE status IN ('ORIGEN_CONFIRMADO', 'EN_PROCESO')
                          AND updated_at < now() - INTERVAL '2 hours'
                        ORDER BY updated_at ASC
                        LIMIT 10;
                        """
                    )
                    cols = [d[0] for d in cur.description]
                    rows = await cur.fetchall()

            if not rows:
                logger.info("[stuck_orders] Sin órdenes atascadas")
                return

            lines = [f"⏰ <b>ATASCO — {len(rows)} orden(es) sin cerrar</b>\n"]
            for row in rows:
                r = dict(zip(cols, row))
                lines.append(
                    f"📦 Orden <b>#{r['public_id']}</b> — {r['status']}\n"
                    f"   {r['origin_country']} → {r['dest_country']} "
                    f"| {float(r['amount_origin']):.2f}\n"
                    f"   ⏱ <b>{float(r['hours_stuck']):.1f}h</b> sin movimiento"
                )

            await self.app.bot.send_message(
                chat_id=int(admin_chat_id),
                text="\n\n".join(lines),
                parse_mode="HTML",
            )
            logger.info("[stuck_orders] Alerta enviada: %d órdenes atascadas", len(rows))

        except Exception:
            logger.exception("[stuck_orders] Error en run_stuck_orders_check")
