from __future__ import annotations

import logging
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
    """
    Scheduler real de tasas (con anti-spam y alertas a grupo):

    Alert destination:
    - Si ALERTS_TELEGRAM_CHAT_ID existe -> manda ahí (grupo Sendmax Alerts)
    - Si no -> manda al ADMIN_TELEGRAM_USER_ID

    Jobs:
    - 9am VET: genera baseline (auto_9am)
    - cada 30m: compara vs baseline:
        BUY_actual >= BUY_9am * 1.03  OR  SELL_actual <= SELL_9am * 0.97
      Si dispara: genera intraday_recalc.

    Anti-spam:
    - Alertas repetidas se limitan por cooldown.
    """

    ALERT_COOLDOWN = timedelta(hours=2)

    def __init__(self, app) -> None:
        self.app = app
        self._last_alert_at: dict[str, datetime] = {}

    def _now_vet_label(self) -> str:
        return datetime.now(tz=VET).strftime("%Y-%m-%d %H:%M")

    def _now_utc(self) -> datetime:
        return datetime.now(timezone.utc)

    def _alerts_chat_id(self) -> int | None:
        if settings.ALERTS_TELEGRAM_CHAT_ID:
            return int(settings.ALERTS_TELEGRAM_CHAT_ID)
        if settings.ADMIN_TELEGRAM_USER_ID:
            return int(settings.ADMIN_TELEGRAM_USER_ID)
        return None

    async def _notify_admin(self, text: str, *, key: str | None = None) -> None:
        chat_id = self._alerts_chat_id()
        if chat_id is None:
            return

        if key:
            last = self._last_alert_at.get(key)
            if last and (self._now_utc() - last) < self.ALERT_COOLDOWN:
                return

        try:
            await self.app.bot.send_message(chat_id=chat_id, text=text)
            if key:
                self._last_alert_at[key] = self._now_utc()
        except Exception:
            pass

    async def run_9am_baseline(self) -> None:
        try:
            res = generate_rates_full(kind="auto_9am", reason=f"Baseline 9am VET {self._now_vet_label()}")
            msg = f"✅ Tasas 9am generadas. Versión #{res.version_id}\nPaíses OK: {len(res.countries_ok)} | Fallaron: {len(res.countries_failed)}"
            logger.info(msg)
            await self._notify_admin(msg, key="baseline_ok")

            if res.any_unverified:
                await self._notify_admin(
                    "⚠️ Aviso: en la versión 9am se usó al menos un anuncio NO verificado (fallback).",
                    key="baseline_unverified",
                )

            if res.countries_failed:
                await self._notify_admin(
                    f"⚠️ Aviso: países sin datos en 9am: {', '.join(res.countries_failed)}",
                    key="baseline_failed",
                )

        except Exception as e:
            logger.exception("Error en baseline 9am: %s", e)
            await self._notify_admin(f"⚠️ Error generando baseline 9am: {e}", key="baseline_error")

    async def run_30m_check(self) -> None:
        baseline_version_id = latest_9am_version_id_today()
        if not baseline_version_id:
            logger.info("[rates] 30m: sin baseline auto_9am, skip")
            return

        baseline = load_country_prices_for_version(baseline_version_id)
        if not baseline:
            logger.info("[rates] 30m: baseline sin country prices, skip")
            return

        client = BinanceP2PClient()
        triggers: list[str] = []
        any_unverified_now = False
        failed_now: list[str] = []

        try:
            ref_map = get_setting_json("p2p_reference_amounts") or {}

            def _trans_amount_for_fiat(fiat: str, fallback: float) -> float:
                try:
                    v = ref_map.get(fiat)
                    return float(v) if v is not None else float(fallback)
                except Exception:
                    return float(fallback)
            for code, cfg in COUNTRIES.items():
                if code not in baseline:
                    continue

                try:
                    buy_q = client.fetch_first_price(
                        fiat=cfg.fiat, trade_type="BUY", pay_methods=cfg.buy_methods[:1], trans_amount=_trans_amount_for_fiat(cfg.fiat, cfg.trans_amount)
                    )
                    sell_q = client.fetch_first_price(
                        fiat=cfg.fiat, trade_type="SELL", pay_methods=cfg.sell_methods[:1], trans_amount=_trans_amount_for_fiat(cfg.fiat, cfg.trans_amount)
                    )
                    if not (buy_q.is_verified and sell_q.is_verified):
                        any_unverified_now = True

                    buy_now = Decimal(str(buy_q.price))
                    sell_now = Decimal(str(sell_q.price))

                except Exception:
                    failed_now.append(code)
                    continue

                buy_base = Decimal(str(baseline[code]["buy"]))
                sell_base = Decimal(str(baseline[code]["sell"]))

                thr = Decimal(str(get_setting_float('pricing_fluctuation_threshold','percent', 0.03)))
                buy_trigger = Decimal('1') + thr
                sell_trigger = Decimal('1') - thr

                if buy_now >= (buy_base * buy_trigger):
                    pct = (buy_now / buy_base - Decimal("1")) * Decimal("100")
                    triggers.append(f"BUY {code} +{pct.quantize(Decimal('0.01'))}%")

                if sell_now <= (sell_base * sell_trigger):
                    pct = (Decimal("1") - sell_now / sell_base) * Decimal("100")
                    triggers.append(f"SELL {code} -{pct.quantize(Decimal('0.01'))}%")

            if failed_now:
                await self._notify_admin(
                    f"⚠️ Tasas 30m: países con error Binance: {', '.join(failed_now)}",
                    key=f"30m_failed_{','.join(sorted(failed_now))}",
                )

            if any_unverified_now:
                await self._notify_admin(
                    "⚠️ Tasas 30m: se detectó al menos un anuncio NO verificado (fallback) en consulta actual.",
                    key="30m_unverified",
                )

            if not triggers:
                logger.info("[rates] 30m: sin cambios >=3% vs baseline, no action")
                return

            reason = " | ".join(triggers[:6])
            await self._notify_admin(f"📈 Disparador tasas 30m: {reason}\nGenerando nueva versión…", key="30m_trigger")

            res = generate_rates_full(kind="intraday_recalc", reason=f"30m trigger: {reason}")
            await self._notify_admin(
                f"✅ Nueva versión generada #{res.version_id} (intraday). OK={len(res.countries_ok)} FAIL={len(res.countries_failed)}",
                key="30m_generated",
            )

        finally:
            client.close()
