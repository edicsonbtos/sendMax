"""Router: Health check"""

import logging
from fastapi import APIRouter
from ..db import fetch_one
from ..config import SECRET_KEY, BACKOFFICE_API_KEY

router = APIRouter(tags=["diagnostics"])
logger = logging.getLogger(__name__)


@router.get("/health")
def health():
    """
    Health check con verificación de conectividad a la base de datos y secretos.
    """
    db_ok = False
    db_error = None

    try:
        result = fetch_one("SELECT 1 AS ok")
        db_ok = result is not None and result.get("ok") == 1
    except Exception as e:
        db_error = str(e)
        logger.warning("Health check DB failed: %s", e)

    secret_key_present = bool(SECRET_KEY)
    api_key_present = bool(BACKOFFICE_API_KEY)
    degraded = not (db_ok and secret_key_present and api_key_present)

    response = {
        "ok": db_ok,
        "status": "ok" if not degraded else "degraded",
        "service": "backoffice-api",
        "version": "0.7.0",
        "db": "connected" if db_ok else "unreachable",
        "secret_key_present": secret_key_present,
        "api_key_present": api_key_present,
        "degraded": degraded,
    }

    if db_error:
        response["db_error"] = db_error

    return response
