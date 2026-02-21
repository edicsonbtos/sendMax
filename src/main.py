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
from src.db.connection import close_pool, wait_db_ready, is_pool_open
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

bot_app = build_bot()
rates_scheduler = RatesScheduler(bot_app)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Sequential Setup
    try:
        # 1. DB (Fail-fast)
        await wait_db_ready()
    except Exception as e:
        logger.error(f"FATAL: Database initialization failed: {e}")
        raise

    # 2. PTB Initialize
    logger.info("Starting PTB Application...")
    await bot_app.initialize()

    # 3. Scheduler + Guards
    async def job_9am(context):
        if not is_pool_open():
            logger.warning("skipped job_9am: DB pool not ready")
            return
        await rates_scheduler.run_9am_baseline()

    async def job_30m(context):
        if not is_pool_open():
            logger.warning("skipped job_30m: DB pool not ready")
            return
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
    logger.info("Rates scheduler registered")

    # 4. Webhook + Start
    if settings.WEBHOOK_URL:
        url = f"{settings.WEBHOOK_URL}/{settings.TELEGRAM_BOT_TOKEN}"
        await bot_app.bot.set_webhook(url=url, allowed_updates=["message", "callback_query"])
        logger.info(f"Webhook set: {url}")

    await bot_app.start()

    yield

    # Teardown
    logger.info("Shutting down Sendmax...")
    try:
        await bot_app.stop()
        await bot_app.shutdown()
    except Exception as e:
        logger.error(f"Error stopping PTB: {e}")

    await close_pool()

app = FastAPI(lifespan=lifespan)

@app.post(f"/{settings.TELEGRAM_BOT_TOKEN}")
async def telegram_webhook(request: Request):
    """Endpoint to receive Telegram updates."""
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

    try:
        if settings.WEBHOOK_URL:
            logger.info(f"Running in WEBHOOK mode (FastAPI) on port {settings.PORT}")
            uvicorn.run(app, host="0.0.0.0", port=settings.PORT, log_level="info")
        else:
            logger.info("Running in POLLING mode (Development)")
            bot_app.run_polling(allowed_updates=["message", "callback_query"])
    finally:
        if not settings.WEBHOOK_URL:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(close_pool())
                else:
                    asyncio.run(close_pool())
            except Exception:
                pass

if __name__ == "__main__":
    main()
