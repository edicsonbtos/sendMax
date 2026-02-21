from __future__ import annotations

import logging
import asyncio
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from src.config.settings import settings
from src.db.settings_store import get_setting_float, get_setting_json
from src.integrations.binance_p2p import BinanceP2PClient
from src.integrations.p2p_config import COUNTRIES
from src.db.repositories.rates_baseline_repo import load_country_prices_for_version, latest_9am_version_id_today
from src.rates_generator import generate_rates_full

logger = logging.getLogger("rates_scheduler")
VET = ZoneInfo("America/Caracas")

class RatesScheduler:
    ALERT_COOLDOWN = timedelta(hours=2)

    def __init__(self, app) -> None:
        self.app = app
        self._last_alert_at: dict[str, datetime] = {}

    def _now_vet_label(self) -> str:
        return datetime.now(tz=VET).strftime("%Y-%m-%d %H:%M")

    async def _notify_admin(self, text: str, *, key: str | None = None) -> None:
        chat_id = settings.ALERTS_TELEGRAM_CHAT_ID or settings.ADMIN_TELEGRAM_USER_ID
        if not chat_id: return

        if key:
            last = self._last_alert_at.get(key)
            if last and (datetime.now(timezone.utc) - last) < self.ALERT_COOLDOWN:
                return

        try:
            await self.app.bot.send_message(chat_id=int(chat_id), text=text)
            if key:
                self._last_alert_at[key] = datetime.now(timezone.utc)
        except Exception:
            pass

    async def run_9am_baseline(self) -> None:
        try:
            res = await generate_rates_full(kind="auto_9am", reason=f"Baseline 9am VET {self._now_vet_label()}")
            msg = f"📈 Tasas 9am generadas. Versión #{res.version_id}\nPaíses OK: {len(res.countries_ok)} | Fallaron: {len(res.countries_failed)}"
            logger.info(msg)
            await self._notify_admin(msg, key="baseline_ok")
        except Exception as e:
            logger.exception("Error in baseline 9am: %s", e)
            await self._notify_admin(f"⚠️ Error generando baseline 9am: {e}", key="baseline_error")

    async def run_30m_check(self) -> None:
        baseline_version_id = await latest_9am_version_id_today()
        if not baseline_version_id:
            logger.info("[rates] 30m: sin baseline auto_9am, skip")
            return

        baseline = await load_country_prices_for_version(baseline_version_id)
        if not baseline:
            logger.info("[rates] 30m: baseline sin country prices, skip")
            return

        client = BinanceP2PClient()
        triggers: list[str] = []
        any_unverified_now = False
        failed_now: list[str] = []

        try:
            # ALL AWAITED
            ref_map = await get_setting_json("p2p_reference_amounts") or {}
            thr_val = await get_setting_float('pricing_fluctuation_threshold', 'percent', 0.03)
            thr = Decimal(str(thr_val))

            def _trans_amount_for_fiat(fiat: str, fallback: float) -> float:
                v = ref_map.get(fiat)
                return float(v) if v is not None else float(fallback)

            for code, cfg in COUNTRIES.items():
                if code not in baseline: continue
                try:
                    buy_q = await client.fetch_first_price(
                        fiat=cfg.fiat, trade_type="BUY", pay_methods=cfg.buy_methods[:1],
                        trans_amount=_trans_amount_for_fiat(cfg.fiat, cfg.trans_amount)
                    )
                    sell_q = await client.fetch_first_price(
                        fiat=cfg.fiat, trade_type="SELL", pay_methods=cfg.sell_methods[:1],
                        trans_amount=_trans_amount_for_fiat(cfg.fiat, cfg.trans_amount)
                    )

                    if not (buy_q.is_verified and sell_q.is_verified):
                        any_unverified_now = True

                    buy_now = Decimal(str(buy_q.price))
                    sell_now = Decimal(str(sell_q.price))
                    buy_base = Decimal(str(baseline[code]["buy"]))
                    sell_base = Decimal(str(baseline[code]["sell"]))

                    if buy_now >= (buy_base * (Decimal('1') + thr)):
                        pct = (buy_now / buy_base - Decimal("1")) * Decimal("100")
                        triggers.append(f"BUY {code} +{pct.quantize(Decimal('0.01'))}%")

                    if sell_now <= (sell_base * (Decimal('1') - thr)):
                        pct = (Decimal("1") - sell_now / sell_base) * Decimal("100")
                        triggers.append(f"SELL {code} -{pct.quantize(Decimal('0.01'))}%")

                except Exception:
                    failed_now.append(code)

            if not triggers:
                logger.info("[rates] 30m: no changes >= threshold, no action")
                return

            reason = " | ".join(triggers[:6])
            await self._notify_admin(f"🚨 Disparador tasas 30m: {reason}\nGenerando nueva versión…", key="30m_trigger")
            res = await generate_rates_full(kind="intraday_recalc", reason=f"30m trigger: {reason}")
            await self._notify_admin(f"✅ Nueva versión #{res.version_id} (intraday). OK={len(res.countries_ok)}", key="30m_generated")

        finally:
            await client.close()
