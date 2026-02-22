from __future__ import annotations

import asyncio
import os

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
        # 1. DB (Non-blocking con timeout)
        logger.info("Waiting for database connection...")
        await asyncio.wait_for(wait_db_ready(), timeout=30.0)
        logger.info("Database connected successfully")
    except asyncio.TimeoutError:
        logger.warning("Database connection timeout - bot will start anyway")
    except Exception as e:
        logger.warning(f"Database initialization failed: {e} - bot will start anyway")

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
        url = f"{settings.WEBHOOK_URL}/webhook"
        print(f"\n--- SETTING WEBHOOK ---")
        print(f"URL: {url}")
        logger.info(f"Setting webhook to: {url}")
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

@app.get("/")
async def root():
    return {"status": "ok"}

@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Endpoint to receive Telegram updates."""
    data = await request.json()
    try:
        upd_id = data.get("update_id")
        logger.info(f"[WEBHOOK] update_id={upd_id}")
    except Exception:
        pass

    update = Update.de_json(data, bot_app.bot)

    # Encolar para que PTB lo procese en su loop normal
    await bot_app.update_queue.put(update)

    # Responder rapido a Telegram
    return Response(status_code=200)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "sendmax-bot"}

def main() -> None:
    setup_logging()
    _configure_warnings()

    try:
        if settings.WEBHOOK_URL:
            port = int(os.environ.get("PORT", 8080))
            print(f"Iniciando servidor en el puerto: {port}")
            logger.info(f"Running in WEBHOOK mode (FastAPI) on port {port}")
            uvicorn.run(app, host="0.0.0.0", port=port, log_level="info", access_log=True)
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
