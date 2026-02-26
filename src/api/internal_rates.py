from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel
import os
import logging
from src.rates_generator import generate_rates_full

router = APIRouter(prefix="/internal/rates", tags=["internal_rates"])
logger = logging.getLogger(__name__)

class InternalRegenerateRequest(BaseModel):
    kind: str = "manual"
    reason: str = "Regeneración interna"

@router.post("/regenerate")
async def internal_regenerate_rates(
    body: InternalRegenerateRequest,
    request: Request,
    x_internal_key: str = Header(None, alias="X-INTERNAL-KEY")
):
    """Endpoint interno para disparar la regeneración de tasas desde backoffice_api."""
    expected_key = os.getenv("INTERNAL_API_KEY")

    if not expected_key:
        logger.error("INTERNAL_API_KEY no configurada en el bot")
        raise HTTPException(status_code=500, detail="Configuración incompleta")

    if x_internal_key != expected_key:
        logger.warning(f"Intento de acceso interno no autorizado desde {request.client.host if request.client else 'unknown'}")
        raise HTTPException(status_code=403, detail="No autorizado")

    # Opt-in check
    from src.config.settings import settings
    if not settings.ALLOW_REMOTE_RATES_REGEN:
        logger.info("[INTERNAL] Regeneración de tasas omitida: ALLOW_REMOTE_RATES_REGEN=False")
        return {"ok": False, "detail": "Regeneración remota no habilitada"}

    try:
        logger.info(f"[INTERNAL] Regenerando tasas solicitado. Kind: {body.kind}, Reason: {body.reason}")
        result = await generate_rates_full(kind=body.kind, reason=body.reason)

        return {
            "ok": True,
            "version_id": result.version_id,
            "countries_ok": result.countries_ok,
            "countries_failed": result.countries_failed,
            "any_unverified": result.any_unverified
        }
    except Exception as e:
        logger.exception("Error en regeneración interna")
        raise HTTPException(status_code=500, detail=str(e))
