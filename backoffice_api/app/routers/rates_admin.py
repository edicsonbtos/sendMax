"""Router: Administración de Tasas (admin only)"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel
from typing import Optional, List
from ..auth import require_admin
from src.rates_generator import generate_rates_full
from src.db.repositories import rates_repo
from ..db import fetch_one, fetch_all, run_in_transaction
import json

router = APIRouter(prefix="/api/v1/rates", tags=["rates_admin"])
logger = logging.getLogger(__name__)

class RegenerateRequest(BaseModel):
    kind: str = "manual"
    reason: str = "Regeneración desde Backoffice"
    activate: bool = True

def _get_updated_by(auth: dict, request: Request) -> str:
    uid = auth.get("user_id")
    if uid:
        return f"admin:{uid}"
    email = auth.get("email")
    if email:
        return f"admin:{email}"
    return f"admin:{request.client.host if request.client else 'unknown'}"

@router.post("/regenerate")
async def regenerate_rates(
    body: RegenerateRequest,
    request: Request,
    auth: dict = Depends(require_admin)
):
    """Fuerza la regeneración de tasas inmediatamente."""
    try:
        updated_by = _get_updated_by(auth, request)
        user_id = auth.get("user_id")
        logger.info(f"Regenerando tasas solicitado por {updated_by}. Reason: {body.reason}")

        result = await generate_rates_full(kind=body.kind, reason=body.reason)

        # Log en auditoría
        def _log_audit(cur):
            cur.execute(
                """
                INSERT INTO audit_log(actor_user_id, action, entity_type, entity_id, after_json, user_agent, ip)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    user_id, "RATES_REGENERATED", "rate_versions", str(result.version_id),
                    json.dumps({
                        "kind": body.kind,
                        "reason": body.reason,
                        "countries_ok": result.countries_ok,
                        "updated_by": updated_by
                    }),
                    request.headers.get("user-agent"),
                    request.client.host if request.client else None
                )
            )

        run_in_transaction(_log_audit)

        return {
            "ok": True,
            "version_id": result.version_id,
            "countries_ok": result.countries_ok,
            "countries_failed": result.countries_failed,
            "any_unverified": result.any_unverified
        }
    except Exception as e:
        logger.exception("Error regenerando tasas")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/active")
async def get_active_version(auth: dict = Depends(require_admin)):
    """Obtiene la versión de tasas actualmente activa."""
    version = await rates_repo.get_latest_active_rate_version()
    if not version:
        return {"ok": False, "detail": "No hay versión activa"}
    return {"ok": True, "version": version}

@router.get("/versions")
async def list_versions(limit: int = Query(default=20, ge=1, le=100), auth: dict = Depends(require_admin)):
    """Lista las últimas versiones de tasas."""
    versions = await rates_repo.list_rate_versions(limit=limit)
    return {"ok": True, "count": len(versions), "versions": versions}
