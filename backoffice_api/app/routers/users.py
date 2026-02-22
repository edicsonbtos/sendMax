"""
Router de gestion de usuarios (admin only).
- GET  /users              - listar con KYC, balance, busqueda
- GET  /users/{user_id}    - detalle completo
- POST /users              - crear operador con email/password
- PUT  /users/{id}/toggle  - activar/desactivar
- PUT  /users/{id}/password - reset password temporal
"""

import re
import secrets
import logging
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator

from ..auth import verify_api_key
from ..auth_jwt import get_password_hash
from ..db import fetch_one, fetch_all

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

# Campos que no deben salir en respuestas del backoffice API
SENSITIVE_FIELDS = {"hashed_password", "kyc_doc_file_id", "kyc_selfie_file_id"}


def require_admin(auth=Depends(verify_api_key)):
    if not isinstance(auth, dict):
        raise HTTPException(status_code=403, detail="No autorizado")
    if auth.get("role") not in ("admin", "ADMIN"):
        raise HTTPException(status_code=403, detail="Solo administradores")
    return auth


def _ser(row: dict | None) -> dict | None:
    """Serializa row dict de DB a JSON-friendly:
    - Filtra campos sensibles
    - Decimal -> str con 2 decimales (UI)
    - datetime -> isoformat
    - bytes -> utf-8
    """
    if not row:
        return row
    out: dict = {}
    for k, v in row.items():
        if k in SENSITIVE_FIELDS:
            continue
        if v is None:
            out[k] = None
        elif isinstance(v, Decimal):
            out[k] = str(v.quantize(Decimal("0.01")))
        elif isinstance(v, bytes):
            out[k] = v.decode("utf-8", errors="replace")
        elif hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


def _ser_list(rows: list[dict] | None) -> list[dict]:
    return [_ser(r) for r in (rows or [])]  # type: ignore[misc]


class CreateOperatorRequest(BaseModel):
    email: str
    password: str
    full_name: str
    alias: Optional[str] = None
    telegram_user_id: Optional[int] = None  # Optional ahora

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_REGEX.match(v):
            raise ValueError("Email invalido")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password debe tener minimo 8 caracteres")
        return v

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Nombre debe tener minimo 3 caracteres")
        return v

    @field_validator("telegram_user_id")
    @classmethod
    def validate_tg_id(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return None
        if v <= 0:
            raise ValueError("telegram_user_id debe ser > 0 si se envia")
        return v


class ToggleResponse(BaseModel):
    ok: bool
    user_id: int
    is_active: bool


@router.get("")
def list_users(
    search: Optional[str] = Query(None, description="Buscar por alias, nombre o email"),
    auth=Depends(require_admin),
):
    base_sql = """
        SELECT u.id, u.telegram_user_id, u.alias, u.full_name, u.email,
               u.role, u.is_active,
               COALESCE(u.kyc_status, 'PENDING') AS kyc_status,
               u.created_at,
               COALESCE(w.balance_usdt, 0) AS balance_usdt,
               COALESCE(oc.total_orders, 0) AS total_orders
        FROM users u
        LEFT JOIN wallets w ON w.user_id = u.id
        LEFT JOIN (
            SELECT operator_user_id, COUNT(*) AS total_orders
            FROM orders
            GROUP BY operator_user_id
        ) oc ON oc.operator_user_id = u.id
        WHERE u.role IN ('admin', 'operator', 'system')
    """
    if search and search.strip():
        term = "%" + search.strip() + "%"
        sql = base_sql + """
            AND (u.alias ILIKE %s OR u.full_name ILIKE %s OR u.email ILIKE %s)
            ORDER BY u.created_at DESC
        """
        rows = fetch_all(sql, (term, term, term))
    else:
        sql = base_sql + " ORDER BY u.created_at DESC"
        rows = fetch_all(sql)

    return {"count": len(rows or []), "users": _ser_list(rows)}


@router.get("/{user_id}")
def get_user_detail(user_id: int, auth=Depends(require_admin)):
    user = fetch_one(
        """
        SELECT u.id, u.telegram_user_id, u.alias, u.full_name, u.email,
               u.phone, u.address_short, u.role, u.is_active, u.sponsor_id,
               u.payout_country, u.payout_method_text,
               COALESCE(u.kyc_status, 'PENDING') AS kyc_status,
               u.kyc_submitted_at, u.kyc_reviewed_at, u.kyc_review_reason,
               u.created_at, u.updated_at,
               COALESCE(w.balance_usdt, 0) AS balance_usdt
        FROM users u
        LEFT JOIN wallets w ON w.user_id = u.id
        WHERE u.id = %s
        """,
        (user_id,),
    )
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    metrics = fetch_one(
        """
        SELECT
            COALESCE((
                SELECT SUM(amount_usdt) FROM wallet_ledger
                WHERE user_id = %s AND type = 'ORDER_PROFIT'
                  AND created_at >= date_trunc('day', now())
            ), 0) AS profit_today,
            COALESCE((
                SELECT SUM(amount_usdt) FROM wallet_ledger
                WHERE user_id = %s AND type = 'ORDER_PROFIT'
                  AND created_at >= date_trunc('month', now())
            ), 0) AS profit_month,
            COALESCE((
                SELECT SUM(amount_usdt) FROM wallet_ledger
                WHERE user_id = %s AND type = 'SPONSOR_COMMISSION'
                  AND created_at >= date_trunc('month', now())
            ), 0) AS referrals_month
        """,
        (user_id, user_id, user_id),
    )

    ledger = fetch_all(
        """
        SELECT id, amount_usdt, type, ref_order_public_id, memo, created_at
        FROM wallet_ledger
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 15
        """,
        (user_id,),
    )

    withdrawals = fetch_all(
        """
        SELECT id, amount_usdt, status, dest_text, country,
               fiat, fiat_amount, reject_reason,
               created_at, resolved_at
        FROM withdrawals
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 10
        """,
        (user_id,),
    )

    ref_row = fetch_one(
        "SELECT COUNT(*) AS cnt FROM users WHERE sponsor_id = %s",
        (user_id,),
    )

    orders = fetch_all(
        """
        SELECT public_id, origin_country, dest_country,
               amount_origin, payout_dest, profit_usdt,
               status, created_at
        FROM orders
        WHERE operator_user_id = %s
        ORDER BY created_at DESC
        LIMIT 10
        """,
        (user_id,),
    )

    return {
        "user": _ser(user),
        "metrics": _ser(metrics) if metrics else {
            "profit_today": "0.00",
            "profit_month": "0.00",
            "referrals_month": "0.00",
        },
        "ledger": _ser_list(ledger),
        "withdrawals": _ser_list(withdrawals),
        "referrals_count": int(ref_row["cnt"]) if ref_row else 0,
        "orders": _ser_list(orders),
    }


@router.post("")
def create_operator(data: CreateOperatorRequest, auth=Depends(require_admin)):
    existing = fetch_one("SELECT id FROM users WHERE LOWER(email) = LOWER(%s)", (data.email,))
    if existing:
        raise HTTPException(status_code=400, detail="Email ya registrado")

    hashed = get_password_hash(data.password)
    alias = (data.alias or data.email.split("@")[0]).strip()

    # telegram_user_id puede ser None (usuarios sin Telegram)
    tg_id = data.telegram_user_id

    # Si se envia un tg_id, verificar que no exista ya
    if tg_id is not None:
        tg_exists = fetch_one(
            "SELECT id FROM users WHERE telegram_user_id = %s",
            (tg_id,),
        )
        if tg_exists:
            raise HTTPException(
                status_code=400,
                detail="telegram_user_id ya registrado",
            )

    # Insert directo - NULL es valido en la columna nullable
    row = fetch_one(
        """
        INSERT INTO users
            (telegram_user_id, alias, full_name, email,
             hashed_password, role, is_active)
        VALUES (%s, %s, %s, %s, %s, 'operator', true)
        RETURNING id, alias, email, role
        """,
        (tg_id, alias, data.full_name, data.email, hashed),
        rw=True,
    )
    return {"ok": True, "user": _ser(row)}


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
    temp_pass = secrets.token_urlsafe(10)
    hashed = get_password_hash(temp_pass)
    row = fetch_one(
        "UPDATE users SET hashed_password = %s, updated_at = now() WHERE id = %s RETURNING id",
        (hashed, user_id),
        rw=True,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {"ok": True, "temp_password": temp_pass}