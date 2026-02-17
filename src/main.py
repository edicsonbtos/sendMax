from __future__ import annotations

import logging
import warnings
from datetime import time
from zoneinfo import ZoneInfo

from telegram.warnings import PTBUserWarning

from src.config.logging import setup_logging
from src.config.settings import settings
from src.telegram_app.bot import build_bot
from src.rates_scheduler import RatesScheduler

logger = logging.getLogger("main")
VET = ZoneInfo("America/Caracas")


def _configure_warnings() -> None:
    warnings.filterwarnings(
        "ignore",
        message=r".*CallbackQueryHandler.*will not be tracked for every message.*",
        category=PTBUserWarning,
    )


def main() -> None:
    setup_logging()
    _configure_warnings()

    logger.info("Iniciando Sendmax...")

    app = build_bot()

    rates_scheduler = RatesScheduler(app)

    async def job_9am(context):
        await rates_scheduler.run_9am_baseline()

    async def job_30m(context):
        await rates_scheduler.run_30m_check()

    app.job_queue.run_daily(
        job_9am,
        time=time(hour=9, minute=0, tzinfo=VET),
        name="rates_9am_baseline",
    )

    app.job_queue.run_repeating(
        job_30m,
        interval=30 * 60,
        first=60,
        name="rates_30m_check",
    )

    logger.info("Scheduler tasas: 9am VET + cada 30 min registrado")

    # --- CAMBIO: Polling → Webhook ---
    if settings.WEBHOOK_URL:
        logger.info(f"Modo WEBHOOK: {settings.WEBHOOK_URL}")
        app.run_webhook(
            listen="0.0.0.0",
            port=settings.PORT,
            url_path=settings.TELEGRAM_BOT_TOKEN,
            webhook_url=f"{settings.WEBHOOK_URL}/{settings.TELEGRAM_BOT_TOKEN}",
            allowed_updates=["message", "callback_query"],
        )
    else:
        logger.info("Modo POLLING (desarrollo)")
        app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
