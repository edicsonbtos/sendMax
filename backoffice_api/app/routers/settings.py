"""Router: Admin Settings - Modulo 8 hardened (10x)"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..auth import require_admin
from ..db import fetch_all, fetch_one

router = APIRouter(tags=["settings"])
logger = logging.getLogger(__name__)

# --------------- Constantes ---------------

KEY_REGEX = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
MAX_JSON_BYTES = 32_000
MAX_METHODS_PER_COUNTRY = 30
MAX_STR_LEN = 500

PROTECTED_KEYS = frozenset({"payment_methods"})

SETTING_VALIDATORS: Dict[str, Dict] = {
    "margin_default": {
        "required_fields": {"percent": (float, int)},
        "ranges": {"percent": (0.0, 50.0)},
    },
    "margin_dest_venez": {
        "required_fields": {"percent": (float, int)},
        "ranges": {"percent": (0.0, 50.0)},
    },
    "margin_route_usa_venez": {
        "required_fields": {"percent": (float, int)},
        "ranges": {"percent": (0.0, 50.0)},
    },
}

PAYMENT_COUNTRIES = ["USA", "CHILE", "PERU", "COLOMBIA", "VENEZUELA", "MEXICO", "ARGENTINA"]
_PAYMENT_COUNTRIES_SET = frozenset(PAYMENT_COUNTRIES)


# --------------- Helpers ---------------

def _normalize_json(raw: Any) -> Any:
    if raw is None:
        return None
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw
    return raw


def _safe_json_dumps(val: Any) -> Optional[str]:
    if val is None:
        return None
    return json.dumps(_normalize_json(val))


def _validate_key(key: str) -> str:
    k = (key or "").strip().lower()
    if not KEY_REGEX.match(k):
        raise HTTPException(
            status_code=400,
            detail="Key invalida. Use lower_snake_case 2..64 chars (ej: margin_default).",
        )
    return k


def _validate_payload_size(value_json: Dict[str, Any]) -> None:
    try:
        b = len(json.dumps(value_json, ensure_ascii=False).encode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="value_json no es JSON valido")
    if b > MAX_JSON_BYTES:
        raise HTTPException(
            status_code=413,
            detail="value_json demasiado grande (%d bytes). Max %d." % (b, MAX_JSON_BYTES),
        )


def _validate_setting_value(key: str, value_json: Dict[str, Any]) -> None:
    validator = SETTING_VALIDATORS.get(key)
    if not validator:
        return
    for field, allowed_types in validator.get("required_fields", {}).items():
        if field not in value_json:
            raise HTTPException(
                status_code=400,
                detail="Setting '%s' requiere campo '%s'" % (key, field),
            )
        if not isinstance(value_json[field], allowed_types):
            raise HTTPException(
                status_code=400,
                detail="Setting '%s.%s' debe ser numerico" % (key, field),
            )
    for field, (min_val, max_val) in validator.get("ranges", {}).items():
        val = value_json.get(field)
        if val is not None and not (min_val <= float(val) <= max_val):
            raise HTTPException(
                status_code=400,
                detail="Setting '%s.%s' fuera de rango [%s, %s]: %s" % (key, field, min_val, max_val, val),
            )


def _get_updated_by(auth: dict, request: Request) -> Optional[str]:
    if isinstance(auth, dict):
        uid = auth.get("user_id")
        if uid:
            return "user:%s" % uid
        email = auth.get("email")
        if email:
            return "email:%s" % email
    if request.client:
        return request.client.host
    return None


def _clean_str(v: Any, field_label: str = "campo") -> str:
    s = str(v or "").strip()
    if len(s) > MAX_STR_LEN:
        raise HTTPException(
            status_code=400,
            detail="Texto demasiado largo en %s (max %d chars)." % (field_label, MAX_STR_LEN),
        )
    return s


# --------------- Modelo ---------------

class SettingsUpdate(BaseModel):
    value_json: Dict[str, Any]


# --------------- SETTINGS GENERICOS ---------------

@router.get("/admin/settings")
def get_admin_settings(auth: dict = Depends(require_admin)):
    rows = fetch_all("SELECT key, value_json, updated_at, updated_by FROM settings ORDER BY key")
    return {"items": rows}


@router.put("/admin/settings/{key}")
def put_admin_settings(
    key: str,
    payload: SettingsUpdate,
    request: Request,
    auth: dict = Depends(require_admin),
):
    k = _validate_key(key)

    if k in PROTECTED_KEYS:
        raise HTTPException(
            status_code=400,
            detail="Setting '%s' tiene endpoint dedicado. Use PUT /admin/payment-methods" % k,
        )

    _validate_payload_size(payload.value_json)
    _validate_setting_value(k, payload.value_json)

    before = fetch_one("SELECT key, value_json FROM settings WHERE key=%s", (k,))
    before_json = _normalize_json(before["value_json"]) if before else None

    updated_by = _get_updated_by(auth, request)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    fetch_one(
        """
        INSERT INTO settings(key, value_json, updated_at, updated_by)
        VALUES (%s, %s::jsonb, now(), %s)
        ON CONFLICT (key) DO UPDATE
          SET value_json = EXCLUDED.value_json,
              updated_at = now(),
              updated_by = EXCLUDED.updated_by
        RETURNING key
        """,
        (k, json.dumps(payload.value_json), updated_by),
        rw=True,
    )

    after = fetch_one("SELECT key, value_json FROM settings WHERE key=%s", (k,))
    after_json = _normalize_json(after["value_json"]) if after else None

    fetch_one(
        """
        INSERT INTO audit_log(
            actor_user_id, action, entity_type, entity_id,
            before_json, after_json, ip, user_agent
        )
        VALUES (NULL, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s)
        RETURNING id
        """,
        (
            "SETTINGS_UPDATED",
            "settings",
            k,
            _safe_json_dumps(before_json),
            _safe_json_dumps(after_json),
            client_ip,
            user_agent,
        ),
        rw=True,
    )

    logger.info("setting_updated key=%s updated_by=%s", k, updated_by)
    return {"ok": True, "key": k, "value_json": after_json}


# --------------- PAYMENT METHODS ---------------

@router.get("/admin/payment-methods")
def get_payment_methods(auth: dict = Depends(require_admin)):
    row = fetch_one("SELECT value_json FROM settings WHERE key=%s", ("payment_methods",))
    data = _normalize_json(row["value_json"]) if row and row["value_json"] else {}
    if not isinstance(data, dict):
        data = {}

    result = {}
    for country in PAYMENT_COUNTRIES:
        country_data = data.get(country, {})
        methods = country_data.get("methods", [])
        result[country] = {
            "methods": methods,
            "active_count": len([m for m in methods if m.get("active") is True]),
            "total_count": len(methods),
        }
    return {"ok": True, "countries": result}


@router.put("/admin/payment-methods")
def put_payment_methods(
    payload: SettingsUpdate,
    request: Request,
    auth: dict = Depends(require_admin),
):
    _validate_payload_size(payload.value_json)
    raw_data = payload.value_json
    data: Dict[str, Any] = {}

    for country_raw, country_val in raw_data.items():
        country = (country_raw or "").strip().upper()
        if country not in _PAYMENT_COUNTRIES_SET:
            raise HTTPException(status_code=400, detail="Pais no valido: %s" % country_raw)

        if not isinstance(country_val, dict):
            raise HTTPException(
                status_code=400,
                detail="Valor para %s debe ser objeto" % country,
            )

        methods = country_val.get("methods", [])
        if not isinstance(methods, list):
            raise HTTPException(status_code=400, detail="'methods' en %s debe ser lista" % country)

        if len(methods) > MAX_METHODS_PER_COUNTRY:
            raise HTTPException(
                status_code=400,
                detail="Demasiados metodos en %s. Max %d." % (country, MAX_METHODS_PER_COUNTRY),
            )

        validated_methods = []
        for i, m in enumerate(methods):
            pos = i + 1
            if not isinstance(m, dict):
                raise HTTPException(
                    status_code=400,
                    detail="Metodo %d en %s debe ser objeto" % (pos, country),
                )

            name = _clean_str(m.get("name"), "nombre metodo %d en %s" % (pos, country))
            if not name:
                raise HTTPException(
                    status_code=400,
                    detail="Metodo %d en %s sin nombre valido" % (pos, country),
                )

            holder = _clean_str(m.get("holder", ""), "holder metodo %d" % pos)
            details = _clean_str(m.get("details", ""), "details metodo %d" % pos)

            active = bool(m.get("active", True))

            order_raw = m.get("order", pos)
            try:
                order_val = int(order_raw)
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=400,
                    detail="order invalido en %s metodo %d" % (country, pos),
                )
            if order_val <= 0:
                order_val = pos

            validated_methods.append({
                "name": name,
                "holder": holder,
                "details": details,
                "active": active,
                "order": order_val,
            })

        data[country] = {"methods": validated_methods}

    before = fetch_one("SELECT value_json FROM settings WHERE key=%s", ("payment_methods",))
    before_json = _normalize_json(before["value_json"]) if before else None

    updated_by = _get_updated_by(auth, request)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    fetch_one(
        """
        INSERT INTO settings(key, value_json, updated_at, updated_by)
        VALUES (%s, %s::jsonb, now(), %s)
        ON CONFLICT (key) DO UPDATE
          SET value_json = EXCLUDED.value_json,
              updated_at = now(),
              updated_by = EXCLUDED.updated_by
        RETURNING key
        """,
        ("payment_methods", json.dumps(data), updated_by),
        rw=True,
    )

    fetch_one(
        """
        INSERT INTO audit_log(
            actor_user_id, action, entity_type, entity_id,
            before_json, after_json, ip, user_agent
        )
        VALUES (NULL, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s)
        RETURNING id
        """,
        (
            "PAYMENT_METHODS_UPDATED",
            "settings",
            "payment_methods",
            _safe_json_dumps(before_json),
            _safe_json_dumps(data),
            client_ip,
            user_agent,
        ),
        rw=True,
    )

    logger.info("payment_methods_updated updated_by=%s", updated_by)
    return {"ok": True, "saved": True}