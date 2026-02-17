"""
Router de gestion de usuarios (admin only).
- GET /users - listar usuarios
- POST /users - crear operador con email/password
- PUT /users/{id}/toggle - activar/desactivar
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from ..auth import verify_api_key
from ..auth_jwt import get_password_hash
from ..db import fetch_one, fetch_all

router = APIRouter(prefix="/users", tags=["Users"])


def require_admin(auth=Depends(verify_api_key)):
    if not isinstance(auth, dict):
        raise HTTPException(status_code=403, detail="No autorizado")
    if auth.get("role") not in ("admin", "ADMIN"):
        raise HTTPException(status_code=403, detail="Solo administradores")
    return auth


class CreateOperatorRequest(BaseModel):
    email: str
    password: str
    full_name: str
    alias: Optional[str] = None
    telegram_user_id: Optional[int] = None


class ToggleResponse(BaseModel):
    ok: bool
    user_id: int
    is_active: bool


@router.get("")
def list_users(auth=Depends(require_admin)):
    rows = fetch_all(
        """
        SELECT id, telegram_user_id, alias, full_name, email,
               role, is_active, created_at
        FROM users
        WHERE role IN ('admin', 'operator')
        ORDER BY created_at DESC
        """
    )
    users = []
    for r in rows:
        users.append({
            "id": r["id"],
            "telegram_user_id": r["telegram_user_id"],
            "alias": r["alias"],
            "full_name": r["full_name"],
            "email": r["email"],
            "role": r["role"],
            "is_active": r["is_active"],
            "has_password": bool(r.get("email")),
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        })
    return {"count": len(users), "users": users}


@router.post("")
def create_operator(data: CreateOperatorRequest, auth=Depends(require_admin)):
    existing = fetch_one("SELECT id FROM users WHERE email = %s", (data.email,))
    if existing:
        raise HTTPException(status_code=400, detail="Email ya registrado")

    hashed = get_password_hash(data.password)
    tg_id = data.telegram_user_id or 0
    alias = data.alias or data.email.split("@")[0]

    row = fetch_one(
        """
        INSERT INTO users (telegram_user_id, alias, full_name, email, hashed_password, role, is_active)
        VALUES (%s, %s, %s, %s, %s, 'operator', true)
        RETURNING id, alias, email, role
        """,
        (tg_id, alias, data.full_name, data.email, hashed),
        rw=True,
    )

    return {"ok": True, "user": row}


@router.put("/{user_id}/toggle")
def toggle_user(user_id: int, auth=Depends(require_admin)):
    row = fetch_one(
        """
        UPDATE users SET is_active = NOT is_active, updated_at = now()
        WHERE id = %s
        RETURNING id, is_active
        """,
        (user_id,),
        rw=True,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return ToggleResponse(ok=True, user_id=row["id"], is_active=row["is_active"])


@router.put("/{user_id}/password")
def reset_password(user_id: int, auth=Depends(require_admin)):
    """Reset password a un valor temporal."""
    temp_pass = "Sendmax2026!"
    hashed = get_password_hash(temp_pass)

    row = fetch_one(
        "UPDATE users SET hashed_password = %s, updated_at = now() WHERE id = %s RETURNING id",
        (hashed, user_id),
        rw=True,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return {"ok": True, "temp_password": temp_pass}
