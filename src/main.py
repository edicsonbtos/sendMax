from __future__ import annotations

import asyncio
import os
import secrets
import logging
import warnings
from contextlib import asynccontextmanager
from datetime import time
from zoneinfo import ZoneInfo

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from telegram import Update
from telegram.warnings import PTBUserWarning

from src.config.logging import setup_logging
from src.config.settings import settings
from src.db.connection import close_pool, wait_db_ready, is_pool_open
from src.rates_scheduler import RatesScheduler
from src.telegram_app.bot import build_bot
from src.api import internal_rates
from src.api import operators_router, ranking_router, rates_live_router, auth_router

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

    # bot_app.job_queue.run_repeating(
    #     job_vault_alert,
    #     interval=30 * 60,   # cada 30 minutos
    #     first=90,           # primera ejecución a los 90s (escalonado con rates check)
    #     name="vault_alert_check",
    # )
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
        # Generar o leer webhook secret para verificar que los updates vienen de Telegram
        global _webhook_secret_token
        _webhook_secret_token = os.environ.get("WEBHOOK_SECRET_TOKEN") or secrets.token_urlsafe(32)
        logger.info("Setting webhook to: %s (with secret_token verification)", url)
        await bot_app.bot.set_webhook(
            url=url,
            allowed_updates=["message", "callback_query"],
            secret_token=_webhook_secret_token,
        )
        logger.info("Webhook set: %s", url)

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


# Webhook secret token (se genera en lifespan, se verifica en /webhook)
_webhook_secret_token: str | None = None
_last_webhook_ts: float = 0.0

IS_PRODUCTION = os.environ.get("RAILWAY_ENVIRONMENT") == "production" or bool(os.environ.get("WEBHOOK_URL"))

app = FastAPI(
    lifespan=lifespan,
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
)

# Configuración CORS — dominios específicos (sin wildcard)
_ALLOWED_ORIGINS = [
    "https://sendmax-web-production.up.railway.app",
    "https://admin-web-production-442a.up.railway.app",
]
if not IS_PRODUCTION:
    _ALLOWED_ORIGINS.append("http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security Headers
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if IS_PRODUCTION:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# --- Unified Logging & Security: Error Handler ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    from fastapi.responses import JSONResponse
    from fastapi.exceptions import HTTPException
    
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"ok": False, "detail": exc.detail},
        )
    
    logger.error(f"Unhandled Server Error: {request.method} {request.url.path} -> {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"ok": False, "detail": "Error interno del servidor"}
    )

app.include_router(internal_rates.router)
app.include_router(auth_router, prefix="/auth", tags=["Auth"])

# Auth de operadores
from src.api.auth_operators import router as operator_auth_router
app.include_router(operator_auth_router)
app.include_router(operators_router)
app.include_router(ranking_router)
app.include_router(rates_live_router)

from src.api.beneficiaries import router as beneficiaries_router
app.include_router(beneficiaries_router)

from src.api.routes import client_ranking, clients
app.include_router(client_ranking.router)
app.include_router(clients.router)


@app.get("/")
async def root():
    return {"status": "ok", "service": "sendmax-bot"}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "sendmax-bot"}

@app.get("/admin/health/bot")
async def admin_bot_health():
    import time
    global _last_webhook_ts
    
    # Check PTB connectivity
    try:
        me = await bot_app.bot.get_me()
        tg_status = "ok"
        bot_usr = me.username
    except Exception as e:
        tg_status = "down"
        bot_usr = str(e)
        
    diff = time.time() - _last_webhook_ts if _last_webhook_ts > 0 else -1
    
    return {
        "status": "ok" if tg_status == "ok" else "error",
        "telegram_api": tg_status,
        "bot_username": bot_usr,
        "last_webhook_ts": _last_webhook_ts,
        "seconds_since_last_webhook": int(diff)
    }


@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Endpoint to receive Telegram updates (con verificación de firma)."""
    import time
    global _last_webhook_ts
    _last_webhook_ts = time.time()
    
    # Verificar que el request viene de Telegram (secret_token header)
    if _webhook_secret_token:
        incoming_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if incoming_token != _webhook_secret_token:
            logger.warning("Webhook request con secret_token inválido (posible spoofing)")
            return Response(status_code=403)

    data = await request.json()
    try:
        upd_id = data.get("update_id")
        logger.info("[WEBHOOK] update_id=%s", upd_id)
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
