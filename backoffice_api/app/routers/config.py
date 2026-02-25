"""Router: Configuración dinámica (comisiones, splits)"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from decimal import Decimal
from ..db import run_in_transaction, fetch_one
from ..auth import require_admin
import json
import os
import httpx
import logging

router = APIRouter(prefix="/api/v1/config", tags=["config"])
logger = logging.getLogger(__name__)

class CommissionRouteUpdate(BaseModel):
    route: str  # "CHILE_VENEZUELA"
    percent: Decimal = Field(ge=0, le=0.5, decimal_places=4)

class ProfitSplitUpdate(BaseModel):
    operator_with_sponsor: Decimal = Field(ge=0, le=1)
    sponsor: Decimal = Field(ge=0, le=1)
    operator_solo: Decimal = Field(ge=0, le=1)

class MarginUpdateRequest(BaseModel):
    margin_default: float | None = Field(default=None, ge=0, le=0.5)
    margin_dest_venez: float | None = Field(default=None, ge=0, le=0.5)
    margin_route_usa_venez: float | None = Field(default=None, ge=0, le=0.5)
    regenerate: bool = False

def _get_updated_by(auth: dict, request: Request) -> str:
    uid = auth.get("user_id")
    if uid:
        return f"admin:{uid}"
    email = auth.get("email")
    if email:
        return f"admin:{email}"
    return f"admin:{request.client.host if request.client else 'unknown'}"

@router.get("/commissions")
def get_all_commissions(auth: dict = Depends(require_admin)):
    """Lista todas las configuraciones de comisión."""
    configs = {}

    # Rutas específicas
    routes = fetch_one("SELECT value_json FROM settings WHERE key='commission_routes'")
    if routes:
        configs["routes"] = json.loads(routes["value_json"]) if isinstance(routes["value_json"], str) else routes["value_json"]

    # Defaults
    for key in ["margin_default", "margin_dest_venez", "margin_route_usa_venez", "profit_split"]:
        row = fetch_one("SELECT value_json FROM settings WHERE key=%s", (key,))
        if row:
            configs[key] = json.loads(row["value_json"]) if isinstance(row["value_json"], str) else row["value_json"]

    return configs

@router.put("/commission/route")
def update_commission_route(body: CommissionRouteUpdate, request: Request, auth: dict = Depends(require_admin)):
    """Actualiza comisión para ruta específica."""
    updated_by = _get_updated_by(auth, request)
    user_id = auth.get("user_id")
    def _update(cur):
        # Leer actual
        cur.execute("SELECT value_json FROM settings WHERE key='commission_routes' FOR UPDATE")
        row = cur.fetchone()
        routes = json.loads(row["value_json"]) if row and row["value_json"] else {}

        before_json = json.dumps(routes)
        # Actualizar
        routes[body.route.upper()] = float(body.percent)
        after_json = json.dumps(routes)

        # Guardar
        cur.execute(
            """
            INSERT INTO settings (key, value_json, updated_at, updated_by)
            VALUES ('commission_routes', %s::json, NOW(), %s)
            ON CONFLICT (key) DO UPDATE SET
                value_json = EXCLUDED.value_json,
                updated_at = NOW(),
                updated_by = EXCLUDED.updated_by
            """,
            (after_json, updated_by)
        )

        cur.execute(
            """
            INSERT INTO audit_log(actor_user_id, action, entity_type, entity_id, before_json, after_json, user_agent, ip)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (user_id, "ROUTE_COMMISSION_UPDATED", "settings", "commission_routes", before_json, after_json, request.headers.get("user-agent"), request.client.host if request.client else None)
        )

    run_in_transaction(_update)
    return {"ok": True, "route": body.route, "percent": body.percent}

@router.delete("/commission/route/{route}")
def delete_commission_route(route: str, request: Request, auth: dict = Depends(require_admin)):
    """Elimina la comisión específica para una ruta."""
    updated_by = _get_updated_by(auth, request)
    user_id = auth.get("user_id")
    route_upper = route.upper()

    def _delete(cur):
        cur.execute("SELECT value_json FROM settings WHERE key='commission_routes' FOR UPDATE")
        row = cur.fetchone()
        routes = json.loads(row["value_json"]) if row and row["value_json"] else {}

        if route_upper not in routes:
            return False

        before_json = json.dumps(routes)
        del routes[route_upper]
        after_json = json.dumps(routes)

        cur.execute(
            """
            INSERT INTO settings (key, value_json, updated_at, updated_by)
            VALUES ('commission_routes', %s::json, NOW(), %s)
            ON CONFLICT (key) DO UPDATE SET
                value_json = EXCLUDED.value_json,
                updated_at = NOW(),
                updated_by = EXCLUDED.updated_by
            """,
            (after_json, updated_by)
        )

        cur.execute(
            """
            INSERT INTO audit_log(actor_user_id, action, entity_type, entity_id, before_json, after_json, user_agent, ip)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (user_id, "ROUTE_COMMISSION_DELETED", "settings", "commission_routes", before_json, after_json, request.headers.get("user-agent"), request.client.host if request.client else None)
        )
        return True

    deleted = run_in_transaction(_delete)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Ruta {route_upper} no encontrada")

    return {"ok": True, "deleted": route_upper}

@router.put("/profit-split")
def update_profit_split(body: ProfitSplitUpdate, request: Request, auth: dict = Depends(require_admin)):
    """Actualiza distribución de profit."""
    # Validar que sume sentido (op + sp ≤ 1)
    if body.operator_with_sponsor + body.sponsor > 1:
        raise HTTPException(status_code=400, detail="operator_with_sponsor + sponsor no puede superar 1.0")

    updated_by = _get_updated_by(auth, request)
    user_id = auth.get("user_id")
    def _update(cur):
        cur.execute("SELECT value_json FROM settings WHERE key='profit_split'")
        before = cur.fetchone()

        after_json = json.dumps(body.model_dump(mode='json'))

        cur.execute(
            """
            INSERT INTO settings (key, value_json, updated_at, updated_by)
            VALUES ('profit_split', %s::json, NOW(), %s)
            ON CONFLICT (key) DO UPDATE SET
                value_json = EXCLUDED.value_json,
                updated_at = NOW(),
                updated_by = EXCLUDED.updated_by
            """,
            (after_json, updated_by)
        )

        cur.execute(
            """
            INSERT INTO audit_log(actor_user_id, action, entity_type, entity_id, before_json, after_json, user_agent, ip)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (user_id, "PROFIT_SPLIT_UPDATED", "settings", "profit_split", json.dumps(before["value_json"]) if before else None, after_json, request.headers.get("user-agent"), request.client.host if request.client else None)
        )

    run_in_transaction(_update)
    return {"ok": True, "split": body.model_dump(mode='json')}

@router.post("/margins")
async def update_margins(
    body: MarginUpdateRequest,
    request: Request,
    auth: dict = Depends(require_admin)
):
    """Actualiza márgenes y opcionalmente regenera tasas."""
    updated_by = _get_updated_by(auth, request)
    user_id = auth.get("user_id")

    def _update_db(cur):
        changes = {}
        for key in ["margin_default", "margin_dest_venez", "margin_route_usa_venez"]:
            val = getattr(body, key)
            if val is not None:
                # Leer valor actual para auditoría
                cur.execute("SELECT value_json FROM settings WHERE key=%s", (key,))
                before = cur.fetchone()

                cur.execute(
                    """
                    INSERT INTO settings (key, value_json, updated_at, updated_by)
                    VALUES (%s, %s::json, NOW(), %s)
                    ON CONFLICT (key) DO UPDATE SET
                        value_json = EXCLUDED.value_json,
                        updated_at = NOW(),
                        updated_by = EXCLUDED.updated_by
                    """,
                    (key, json.dumps({"percent": val}), updated_by)
                )
                changes[key] = {"before": before["value_json"] if before else None, "after": {"percent": val}}

        if changes:
            cur.execute(
                """
                INSERT INTO audit_log(actor_user_id, action, entity_type, entity_id, before_json, after_json, user_agent, ip)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    user_id, "MARGINS_UPDATED", "settings", "multiple",
                    json.dumps({k: v["before"] for k, v in changes.items()}),
                    json.dumps({k: v["after"] for k, v in changes.items()}),
                    request.headers.get("user-agent"),
                    request.client.host if request.client else None
                )
            )
        return changes

    run_in_transaction(_update_db)

    regen_result = None
    if body.regenerate:
        bot_url = os.getenv("BOT_INTERNAL_URL")
        internal_key = os.getenv("INTERNAL_API_KEY")
        if bot_url and internal_key:
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.post(
                        f"{bot_url.rstrip('/')}/internal/rates/regenerate",
                        headers={"X-INTERNAL-KEY": internal_key},
                        json={
                            "kind": "manual",
                            "reason": f"Auto-regen tras cambio de márgenes (por {updated_by})"
                        }
                    )
                if resp.status_code == 200:
                    regen_result = resp.json()
                else:
                    regen_result = {"error": f"Bot API error: {resp.status_code}", "detail": resp.text}
            except Exception as e:
                logger.error(f"Error llamando al bot para autoregen: {e}")
                regen_result = {"error": "connection_error", "detail": str(e)}
        else:
            regen_result = {"error": "missing_internal_config"}

    return {
        "ok": True,
        "margins_updated": True,
        "regenerated": body.regenerate,
        "regen_result": regen_result
    }
