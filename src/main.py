from __future__ import annotations

import logging
import warnings
from contextlib import asynccontextmanager
from datetime import time
from zoneinfo import ZoneInfo

import uvicorn
from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.warnings import PTBUserWarning

from src.config.logging import setup_logging
from src.config.settings import settings
from src.db.connection import close_pool
from src.rates_scheduler import RatesScheduler
from src.telegram_app.bot import build_bot

logger = logging.getLogger("main")
VET = ZoneInfo("America/Caracas")


def _configure_warnings() -> None:
    warnings.filterwarnings(
        "ignore",
        message=r".*CallbackQueryHandler.*will not be tracked for every message.*",
        category=PTBUserWarning,
    )


# --- INTEGRACION FASTAPI + PTB ---

bot_app = build_bot()
rates_scheduler = RatesScheduler(bot_app)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup
    logger.info("Iniciando PTB Application...")
    await bot_app.initialize()

    # Scheduler
    async def job_9am(context):
        await rates_scheduler.run_9am_baseline()

    async def job_30m(context):
        await rates_scheduler.run_30m_check()

    bot_app.job_queue.run_daily(
        job_9am,
        time=time(hour=9, minute=0, tzinfo=VET),
        name="rates_9am_baseline",
    )

    bot_app.job_queue.run_repeating(
        job_30m,
        interval=30 * 60,
        first=60,
        name="rates_30m_check",
    )
    logger.info("Scheduler tasas registrado")

    if settings.WEBHOOK_URL:
        url = f"{settings.WEBHOOK_URL}/{settings.TELEGRAM_BOT_TOKEN}"
        await bot_app.bot.set_webhook(url=url, allowed_updates=["message", "callback_query"])
        logger.info(f"Webhook set: {url}")

    await bot_app.start()

    yield

    # Teardown
    logger.info("Cerrando Sendmax...")
    await bot_app.stop()
    await bot_app.shutdown()
    await close_pool()

app = FastAPI(lifespan=lifespan)

@app.post(f"/{settings.TELEGRAM_BOT_TOKEN}")
async def telegram_webhook(request: Request):
    """Endpoint para recibir updates de Telegram."""
    data = await request.json()
    update = Update.de_json(data, bot_app.bot)
    await bot_app.process_update(update)
    return Response(status_code=200)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "sendmax-bot"}


def main() -> None:
    setup_logging()
    _configure_warnings()

    if settings.WEBHOOK_URL:
        logger.info(f"Corriendo en modo WEBHOOK (FastAPI) en puerto {settings.PORT}")
        uvicorn.run(app, host="0.0.0.0", port=settings.PORT, log_level="info")
    else:
        logger.info("Corriendo en modo POLLING (Desarrollo)")
        # En polling usamos el loop de PTB normal
        bot_app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
