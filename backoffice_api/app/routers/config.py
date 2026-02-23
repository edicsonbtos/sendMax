"""Router: Configuración dinámica (comisiones, splits)"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from decimal import Decimal
from ..db import run_in_transaction, fetch_one
from ..auth import verify_api_key
import json

router = APIRouter(tags=["config"])

class CommissionRouteUpdate(BaseModel):
    route: str  # "CHILE_VENEZUELA"
    percent: Decimal = Field(ge=0, le=0.5, decimal_places=4)

class ProfitSplitUpdate(BaseModel):
    operator_with_sponsor: Decimal = Field(ge=0, le=1)
    sponsor: Decimal = Field(ge=0, le=1)
    operator_solo: Decimal = Field(ge=0, le=1)

@router.get("/config/commissions")
def get_all_commissions(auth: dict = Depends(verify_api_key)):
    """Lista todas las configuraciones de comisión."""
    configs = {}

    # Rutas específicas
    routes = fetch_one("SELECT value_json FROM settings WHERE key='commission_routes'")
    if routes:
        configs["routes"] = json.loads(routes["value_json"]) if isinstance(routes["value_json"], str) else routes["value_json"]

    # Defaults
    for key in ["margin_default", "margin_dest_venez", "margin_route_usa_venez"]:
        row = fetch_one("SELECT value_json FROM settings WHERE key=%s", (key,))
        if row:
            configs[key] = json.loads(row["value_json"]) if isinstance(row["value_json"], str) else row["value_json"]

    return configs

@router.put("/config/commission/route")
def update_commission_route(body: CommissionRouteUpdate, auth: dict = Depends(verify_api_key)):
    """Actualiza comisión para ruta específica."""
    if auth.get("role") not in ("admin", "ADMIN"):
        raise HTTPException(status_code=403, detail="Solo admins")

    def _update(cur):
        # Leer actual
        cur.execute("SELECT value_json FROM settings WHERE key='commission_routes' FOR UPDATE")
        row = cur.fetchone()
        routes = json.loads(row["value_json"]) if row and row["value_json"] else {}

        # Actualizar
        routes[body.route.upper()] = float(body.percent)

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
            (json.dumps(routes), f"admin:{auth.get('user_id', 'api')}")
        )

    run_in_transaction(_update)
    return {"ok": True, "route": body.route, "percent": body.percent}

@router.put("/config/profit-split")
def update_profit_split(body: ProfitSplitUpdate, auth: dict = Depends(verify_api_key)):
    """Actualiza distribución de profit."""
    if auth.get("role") not in ("admin", "ADMIN"):
        raise HTTPException(status_code=403, detail="Solo admins")

    # Validar que sume sentido (op + sp ≤ 1)
    if body.operator_with_sponsor + body.sponsor > 1:
        raise HTTPException(status_code=400, detail="operator_with_sponsor + sponsor no puede superar 1.0")

    def _update(cur):
        cur.execute(
            """
            INSERT INTO settings (key, value_json, updated_at, updated_by)
            VALUES ('profit_split', %s::json, NOW(), %s)
            ON CONFLICT (key) DO UPDATE SET
                value_json = EXCLUDED.value_json,
                updated_at = NOW(),
                updated_by = EXCLUDED.updated_by
            """,
            (json.dumps(body.model_dump(mode='json')), f"admin:{auth.get('user_id', 'api')}")
        )

    run_in_transaction(_update)
    return {"ok": True, "split": body.model_dump(mode='json')}
