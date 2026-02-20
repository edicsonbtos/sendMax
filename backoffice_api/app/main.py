"""
Sendmax Backoffice API - Production Ready (M10)

Defensas:
- Graceful Shutdown: cierra pools DB al apagar (Railway redeploy)
- Global Exception Handler: oculta tracebacks, loguea internamente
- Security Headers: X-Frame-Options, HSTS (prod), XSS, nosniff, Referrer-Policy
- Swagger: oculto en produccion
- /health: existe en diagnostics.py (no se duplica aqui)
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
)
from .db import close_pools

logger = logging.getLogger(__name__)

IS_PRODUCTION = os.getenv("ENV", "").lower() == "production"


# ==========================================
# 1. LIFESPAN (Arranque y Apagado Seguro)
# ==========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Sendmax Backoffice API iniciando...")
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
# 3. CORS (con limpieza de espacios)
# ==========================================

raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,https://sendmax-web-production.up.railway.app"
).split(",")
ALLOWED_ORIGINS = [o.strip() for o in raw_origins if o.strip()]

if not ALLOWED_ORIGINS:
    logger.warning("ALLOWED_ORIGINS esta vacio. CORS rechazara todas las peticiones con credenciales.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# 4. SECURITY HEADERS MIDDLEWARE
# ==========================================

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
# 5. GLOBAL EXCEPTION HANDLER
# ==========================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        raise exc

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
# 6. ROUTERS
# ==========================================

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(diagnostics.router)
app.include_router(metrics.router)
app.include_router(orders.router)
app.include_router(origin_wallets.router)
app.include_router(settings.router)
app.include_router(alerts.router)
app.include_router(corrections.router)