from __future__ import annotations

"""
src/main.py

Entry-point único del proyecto.

- Configura logging.
- Filtra warnings ruidosos de PTB sobre per_message/per_* (no son errores).
- Construye el bot con build_bot().
- Registra scheduler de tasas.
- Inicia polling.
"""

import logging
import warnings
from datetime import time
from zoneinfo import ZoneInfo

from telegram.warnings import PTBUserWarning

from src.config.logging import setup_logging
from src.telegram_app.bot import build_bot
from src.rates_scheduler import RatesScheduler

logger = logging.getLogger("main")
VET = ZoneInfo("America/Caracas")


def _configure_warnings() -> None:
    """
    Silencia SOLO el warning informativo de python-telegram-bot sobre ConversationHandler
    cuando se usan CallbackQueryHandlers con per_message=False.

    Importante:
    - No silenciamos DeprecationWarnings ni otros warnings.
    - Esto mantiene logs limpios en producción sin ocultar errores reales.
    """
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

    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
