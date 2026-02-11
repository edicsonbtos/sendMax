"""
Sendmax Backoffice API
Versión refactorizada con routers modulares
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import diagnostics, metrics, orders, origin_wallets, settings, alerts

app = FastAPI(title="Sendmax Backoffice API", version="0.6.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://sendmax-bot.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar routers
app.include_router(diagnostics.router)
app.include_router(metrics.router)
app.include_router(orders.router)
app.include_router(origin_wallets.router)
app.include_router(settings.router)
app.include_router(alerts.router)
