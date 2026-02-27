"""
Sendmax Backoffice API - Production Ready (M10)
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .routers import (
    diagnostics, metrics, orders, origin_wallets,
    settings, alerts, corrections, auth, users,
    config, rates_admin, exports, operator,
)
from .db import close_pools
from .config import validate_config, IS_PRODUCTION, ALLOWED_ORIGINS
from .middleware_limiter import rate_limit_middleware

logger = logging.getLogger(__name__)


# ==========================================
# 1. LIFESPAN (Arranque y Apagado Seguro)
# ==========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Sendmax Backoffice API iniciando...")

    # Validación de configuración en startup
    ok = validate_config()
    if not ok:
        logger.warning("Servicio iniciando en modo DEGRADADO (revisar variables de entorno)")

    yield

    logger.info("Apagando API, cerrando pools de base de datos...")
    try:
        close_pools()
        logger.info("Pools cerrados. Shutdown limpio.")
    except Exception:
        logger.exception("Error cerrando pools en shutdown")


# ==========================================
# 2. INSTANCIA FASTAPI
# ==========================================

app = FastAPI(
    title="Sendmax Backoffice API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None,
)


# ==========================================
# 3. MIDDLEWARES
# ==========================================

# Rate Limiting
@app.middleware("http")
async def apply_rate_limit(request: Request, call_next):
    return await rate_limit_middleware(request, call_next)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
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


# ==========================================
# 4. GLOBAL EXCEPTION HANDLER
# ==========================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        # Propagar HTTPException tal cual
        return JSONResponse(
            status_code=exc.status_code,
            content={"ok": False, "detail": exc.detail},
        )

    logger.error(
        "Error no manejado: %s %s -> %s",
        request.method, request.url.path, exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"ok": False, "detail": "Error interno del servidor."},
    )


# ==========================================
# 5. ROUTERS
# ==========================================

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(config.router)
app.include_router(rates_admin.router)
app.include_router(diagnostics.router)
app.include_router(metrics.router)
app.include_router(orders.router)
app.include_router(origin_wallets.router)
app.include_router(settings.router)
app.include_router(alerts.router)
app.include_router(corrections.router)
app.include_router(exports.router)
app.include_router(operator.router)
