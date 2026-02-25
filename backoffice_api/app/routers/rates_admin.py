"""Router: Administración de Tasas (admin only)"""

import logging
import os
import httpx
import json
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel
from typing import Optional, List
from ..auth import require_admin
from ..db import fetch_one, fetch_all, run_in_transaction

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
    """Fuerza la regeneración de tasas llamando al bot vía HTTP interno."""
    try:
        updated_by = _get_updated_by(auth, request)
        user_id = auth.get("user_id")
        bot_url = os.getenv("BOT_INTERNAL_URL")
        internal_key = os.getenv("INTERNAL_API_KEY")

        if not bot_url or not internal_key:
            logger.error("Configuración BOT_INTERNAL_URL o INTERNAL_API_KEY ausente")
            raise HTTPException(status_code=500, detail="Error de configuración interna")

        logger.info(f"Disparando regeneración tasas (via BOT) solicitado por {updated_by}. Reason: {body.reason}")

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{bot_url.rstrip('/')}/internal/rates/regenerate",
                headers={"X-INTERNAL-KEY": internal_key},
                json={
                    "kind": body.kind,
                    "reason": f"{body.reason} (por {updated_by})"
                }
            )

        if resp.status_code != 200:
            logger.error(f"Error llamando al BOT: {resp.status_code} - {resp.text}")
            raise HTTPException(status_code=resp.status_code, detail=f"Bot API error: {resp.text}")

        data = resp.json()
        version_id = data.get("version_id")

        # Log en auditoría
        def _log_audit(cur):
            cur.execute(
                """
                INSERT INTO audit_log(actor_user_id, action, entity_type, entity_id, after_json, user_agent, ip)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    user_id, "RATES_REGENERATED", "rate_versions", str(version_id),
                    json.dumps({
                        "kind": body.kind,
                        "reason": body.reason,
                        "countries_ok": data.get("countries_ok"),
                        "updated_by": updated_by
                    }),
                    request.headers.get("user-agent"),
                    request.client.host if request.client else None
                )
            )

        run_in_transaction(_log_audit)
        return data

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error en regeneración de tasas (gateway)")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/active")
async def get_active_version(auth: dict = Depends(require_admin)):
    """Obtiene la versión de tasas actualmente activa (via SQL directo)."""
    sql = """
        SELECT id, kind, reason, created_at, effective_from, effective_to, is_active
        FROM rate_versions
        WHERE is_active = true
        ORDER BY effective_from DESC
        LIMIT 1;
    """
    version = fetch_one(sql)
    if not version:
        return {"ok": False, "detail": "No hay versión activa"}
    return {"ok": True, "version": version}

@router.get("/versions")
async def list_versions(limit: int = Query(default=20, ge=1, le=100), auth: dict = Depends(require_admin)):
    """Lista las últimas versiones de tasas (via SQL directo)."""
    sql = """
        SELECT id, kind, reason, created_at, effective_from, effective_to, is_active
        FROM rate_versions
        ORDER BY created_at DESC
        LIMIT %s;
    """
    versions = fetch_all(sql, (limit,))
    return {"ok": True, "count": len(versions), "versions": versions}
