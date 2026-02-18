"""Router: Admin Settings"""

import json
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from typing import Any, Dict
from ..db import fetch_one, fetch_all
from ..auth import verify_api_key

router = APIRouter(tags=["settings"])


class SettingsUpdate(BaseModel):
    value_json: Dict[str, Any]


@router.get("/admin/settings")
def get_admin_settings(api_key: str = Depends(verify_api_key)):
    rows = fetch_all("SELECT key, value_json, updated_at, updated_by FROM settings ORDER BY key")
    return {"items": rows}


@router.put("/admin/settings/{key}")
def put_admin_settings(
    key: str,
    payload: SettingsUpdate,
    request: Request,
    api_key: str = Depends(verify_api_key),
):
    before = fetch_one("SELECT key, value_json FROM settings WHERE key=%s", (key,))
    before_json = before["value_json"] if before else None

    fetch_one(
        """
        INSERT INTO settings(key, value_json, updated_at, updated_by)
        VALUES (%s, %s::jsonb, now(), NULL)
        ON CONFLICT (key) DO UPDATE
          SET value_json=EXCLUDED.value_json,
              updated_at=now(),
              updated_by=NULL
        RETURNING key
        """,
        (key, json.dumps(payload.value_json)),
        rw=True,
    )

    after = fetch_one("SELECT key, value_json FROM settings WHERE key=%s", (key,))
    after_json = after["value_json"] if after else None

    fetch_one(
        """
        INSERT INTO audit_log(actor_user_id, action, entity_type, entity_id, before_json, after_json, ip, user_agent)
        VALUES (NULL, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s)
        RETURNING id
        """,
        (
            "SETTINGS_UPDATED",
            "settings",
            key,
            json.dumps(before_json) if before_json is not None else None,
            json.dumps(after_json) if after_json is not None else None,
            request.client.host if request.client else None,
            request.headers.get("user-agent"),
        ),
        rw=True,
    )

    return {"ok": True, "key": key, "value_json": after_json}

# ========================================
# METODOS DE PAGO POR PAIS
# ========================================

PAYMENT_COUNTRIES = ["USA", "CHILE", "PERU", "COLOMBIA", "VENEZUELA", "MEXICO", "ARGENTINA"]


@router.get("/admin/payment-methods")
def get_payment_methods(api_key: str = Depends(verify_api_key)):
    row = fetch_one("SELECT value_json FROM settings WHERE key=%s", ("payment_methods",))
    if row and row["value_json"]:
        data = row["value_json"] if isinstance(row["value_json"], dict) else json.loads(row["value_json"])
    else:
        data = {}
    result = {}
    for country in PAYMENT_COUNTRIES:
        country_data = data.get(country, {})
        methods = country_data.get("methods", [])
        result[country] = {
            "methods": methods,
            "active_count": len([m for m in methods if m.get("active", False)]),
            "total_count": len(methods),
        }
    return {"ok": True, "countries": result}


@router.put("/admin/payment-methods")
def put_payment_methods(
    payload: SettingsUpdate,
    request: Request,
    api_key: str = Depends(verify_api_key),
):
    data = payload.value_json
    for country in data:
        if country.upper() not in PAYMENT_COUNTRIES:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail=f"Pais no valido: {country}")
        methods = data[country].get("methods", [])
        for i, m in enumerate(methods):
            if not m.get("name"):
                from fastapi import HTTPException
                raise HTTPException(status_code=400, detail=f"Metodo {i+1} en {country} sin nombre")
            m.setdefault("holder", "")
            m.setdefault("details", "")
            m.setdefault("active", True)
            m.setdefault("order", i + 1)

    before = fetch_one("SELECT value_json FROM settings WHERE key=%s", ("payment_methods",))
    before_json = before["value_json"] if before else None

    fetch_one(
        """
        INSERT INTO settings(key, value_json, updated_at, updated_by)
        VALUES (%s, %s::jsonb, now(), NULL)
        ON CONFLICT (key) DO UPDATE
          SET value_json=EXCLUDED.value_json,
              updated_at=now(),
              updated_by=NULL
        RETURNING key
        """,
        ("payment_methods", json.dumps(data)),
        rw=True,
    )

    fetch_one(
        """
        INSERT INTO audit_log(actor_user_id, action, entity_type, entity_id, before_json, after_json, ip, user_agent)
        VALUES (NULL, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s)
        RETURNING id
        """,
        (
            "PAYMENT_METHODS_UPDATED",
            "settings",
            "payment_methods",
            json.dumps(before_json) if before_json is not None else None,
            json.dumps(data),
            request.client.host if request.client else None,
            request.headers.get("user-agent"),
        ),
        rw=True,
    )

    return {"ok": True, "saved": True}
