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
