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
from src.api import internal_rates

# === SETUP LOGGING AL IMPORTAR (NO dentro de main()) ===
setup_logging()

warnings.filterwarnings(
    "ignore",
    message=r".*CallbackQueryHandler.*will not be tracked for every message.*",
    category=PTBUserWarning,
)

logger = logging.getLogger("main")
VET = ZoneInfo("America/Caracas")

bot_app = build_bot()
rates_scheduler = RatesScheduler(bot_app)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info("Waiting for database connection...")
        await asyncio.wait_for(wait_db_ready(), timeout=30.0)
        logger.info("Database connected successfully")

        # FIX DB: Asegurar base para sprint 4
        from src.db.connection import get_async_conn
        async with get_async_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute("ALTER TABLE vaults ADD COLUMN IF NOT EXISTS type VARCHAR(50);")
                await cur.execute("ALTER TABLE vaults ADD COLUMN IF NOT EXISTS tipo VARCHAR(50);")
        logger.info("Migración automática de tabla vaults ejecutada correctamente.")

    except asyncio.TimeoutError:
        logger.warning("Database connection timeout - bot will start anyway")
    except Exception as e:
        logger.warning(f"Database initialization failed: {e} - bot will start anyway")

    logger.info("Starting PTB Application...")
    await bot_app.initialize()

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

    # ── Sprint 4: Alert Copilot jobs ──────────────────────────────────────
    async def job_vault_alert(context):
        if not is_pool_open():
            logger.warning("skipped job_vault_alert: DB pool not ready")
            return
        await rates_scheduler.run_vault_alert_check()

    async def job_stuck_orders(context):
        if not is_pool_open():
            logger.warning("skipped job_stuck_orders: DB pool not ready")
            return
        await rates_scheduler.run_stuck_orders_check()

    bot_app.job_queue.run_repeating(
        job_vault_alert,
        interval=30 * 60,   # cada 30 minutos
        first=90,           # primera ejecución a los 90s (escalonado con rates check)
        name="vault_alert_check",
    )
    bot_app.job_queue.run_repeating(
        job_stuck_orders,
        interval=60 * 60,   # cada 60 minutos
        first=120,
        name="stuck_orders_check",
    )
    logger.info("Alert Copilot (Sprint 4) scheduler registered")

    # ── KYC Express: reset automático el domingo a las 00:00 VET ─────────
    async def job_kyc_express_sunday_reset(context):
        """Desactiva el KYC Express el domingo a las 00:00 — exige KYC completo desde entonces."""
        import src.telegram_app.flows.kyc_flow as kyc_module
        kyc_module.KYC_EXPRESS_MODE = False
        logger.warning("KYC_EXPRESS_MODE desactivado automáticamente (reset de domingo).")
        admin_id = getattr(settings, "ADMIN_TELEGRAM_USER_ID", None)
        if admin_id:
            try:
                await context.bot.send_message(
                    chat_id=int(admin_id),
                    text=(
                        "🔒 <b>KYC Express DESACTIVADO</b>\n\n"
                        "El período de acceso rápido (amigos y familia) ha terminado.\n"
                        "Desde ahora, los nuevos operadores deberán completar el KYC completo."
                    ),
                    parse_mode="HTML",
                )
            except Exception:
                pass

    from datetime import time as dt_time
    bot_app.job_queue.run_daily(
        job_kyc_express_sunday_reset,
        time=dt_time(hour=0, minute=0, tzinfo=VET),
        days=(6,),   # 6 = domingo
        name="kyc_express_sunday_reset",
    )
    logger.info("KYC Express Sunday reset job registered")

    if settings.WEBHOOK_URL:
        webhook_url = settings.WEBHOOK_URL.rstrip("/")
        url = f"{webhook_url}/webhook"
        print(f"\n--- SETTING WEBHOOK ---")
        print(f"URL: {url}")
        logger.info(f"Setting webhook to: {url}")
        await bot_app.bot.set_webhook(url=url, allowed_updates=["message", "callback_query"])
        logger.info(f"Webhook set: {url}")

    await bot_app.start()
    logger.info("Bot started successfully")

    yield

    logger.info("Shutting down Sendmax...")
    try:
        await bot_app.stop()
        await bot_app.shutdown()
    except Exception as e:
        logger.error(f"Error stopping PTB: {e}")
    await close_pool()


app = FastAPI(lifespan=lifespan)
app.include_router(internal_rates.router)


@app.get("/")
async def root():
    return {"status": "ok", "service": "sendmax-bot"}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "sendmax-bot"}


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
    await bot_app.update_queue.put(update)
    return Response(status_code=200)


def main() -> None:
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

# PRODUCTION READY - PTB v21.10 / PY 3.13.
