"""Router: Health check"""

import logging
from fastapi import APIRouter
from ..db import fetch_one

router = APIRouter(tags=["diagnostics"])
logger = logging.getLogger(__name__)


@router.get("/health")
def health():
    """
    Health check con verificación de conectividad a la base de datos.
    Ejecuta SELECT 1 contra el pool RO para confirmar que la DB responde.
    """
    db_ok = False
    db_error = None

    try:
        # Timeout corto para no bloquear el healthcheck de Railway
        result = fetch_one("SELECT 1 AS ok")
        db_ok = result is not None and result.get("ok") == 1
    except Exception as e:
        db_error = str(e)
        logger.warning("Health check DB failed: %s", e)

    # Importante: Railway espera un 200 OK.
    # No fallamos el healthcheck completo si la DB está caída temporalmente,
    # pero informamos el estado 'degraded'.

    return {
        "ok": db_ok,
        "status": "ok" if db_ok else "degraded",
        "service": "backoffice-api",
        "version": "0.6.1",
        "db": "connected" if db_ok else "unreachable",
        "db_error": db_error
    }