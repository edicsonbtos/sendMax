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
        result = fetch_one("SELECT 1 AS ok")
        db_ok = result is not None and result.get("ok") == 1
    except Exception as e:
        db_error = str(e)
        logger.warning("Health check DB failed: %s", e)

    status = "ok" if db_ok else "degraded"

    response = {
        "ok": db_ok,
        "status": status,
        "service": "backoffice-api",
        "version": "0.6.0",
        "db": "connected" if db_ok else "unreachable",
    }

    if db_error:
        response["db_error"] = db_error

    return response