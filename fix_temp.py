content = '''\"\"\" Sendmax Backoffice API Version con JWT Auth + Roles \"\"\"

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import diagnostics, metrics, orders, origin_wallets, settings, alerts, corrections, auth, users

app = FastAPI(title="Sendmax Backoffice API", version="0.8.0")

# CORS Origins desde variable de entorno
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,https://sendmax-web-production.up.railway.app"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(diagnostics.router)
app.include_router(metrics.router)
app.include_router(orders.router)
app.include_router(origin_wallets.router)
app.include_router(settings.router)
app.include_router(alerts.router)
app.include_router(corrections.router)


@app.get("/health")
def health():
    return {"status": "ok"}
'''

with open('backoffice_api/app/main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("OK - main.py reescrito con CORS profesional")
