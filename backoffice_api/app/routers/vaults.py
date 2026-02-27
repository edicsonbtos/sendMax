"""
Router: Bóvedas de liquidez (Vaults).

Endpoints:
  GET  /vaults                — Lista todas las bóvedas activas
  GET  /vaults/radar          — Snapshot de liquidez total por tipo
  POST /vaults                — Crear bóveda (admin)
  PUT  /vaults/{id}/adjust    — Ajustar balance manualmente (admin)
  GET  /vaults/provider-liquidation — Fees acumulados por proveedor de cuenta
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth import require_admin, require_operator_or_admin
from ..db import fetch_all, fetch_one

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/vaults", tags=["Vaults"])


# ─── Pydantic schemas ──────────────────────────────────────────────────────────

class VaultCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    vault_type: str = Field("Digital", pattern="^(Digital|Physical|Crypto)$")
    currency: str = Field("USD", max_length=10)
    balance: Decimal = Field(Decimal("0"), ge=0)
    description: Optional[str] = None


class VaultAdjust(BaseModel):
    new_balance: Decimal = Field(..., ge=0)
    note: Optional[str] = None


# ─── Helpers ────────────────────────────────────────────────────────────────────

def _s(v):
    """Serializa Decimal → str, datetime → ISO, None → None."""
    if v is None:
        return None
    if isinstance(v, Decimal):
        return str(v.quantize(Decimal("0.01")))
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return v


def _row(r: dict) -> dict:
    return {k: _s(v) for k, v in r.items()} if r else {}


# ─── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("")
def list_vaults(auth: dict = Depends(require_operator_or_admin)):
    """Lista todas las bóvedas activas con su saldo actual."""
    rows = fetch_all(
        """
        SELECT id, name, vault_type, currency, balance, description, is_active, updated_at
        FROM vaults
        ORDER BY vault_type, name
        """
    )
    return {"ok": True, "vaults": [_row(r) for r in (rows or [])]}


@router.get("/radar")
def vault_radar(auth: dict = Depends(require_operator_or_admin)):
    """
    Snapshot de liquidez total agrupado por tipo de bóveda.
    Útil para el panel de control del admin.
    """
    rows = fetch_all(
        """
        SELECT vault_type,
               currency,
               COUNT(*) AS count,
               SUM(balance) AS total_balance
        FROM vaults
        WHERE is_active = true
        GROUP BY vault_type, currency
        ORDER BY vault_type, currency
        """
    )
    total_row = fetch_one(
        "SELECT COALESCE(SUM(balance), 0) AS grand_total FROM vaults WHERE is_active = true AND currency = 'USD'"
    )
    return {
        "ok": True,
        "by_type": [_row(r) for r in (rows or [])],
        "grand_total_usd": _s(total_row.get("grand_total") if total_row else 0),
    }


@router.post("")
def create_vault(body: VaultCreate, auth: dict = Depends(require_admin)):
    """Crea una nueva bóveda (solo admin)."""
    existing = fetch_one("SELECT id FROM vaults WHERE name = %s LIMIT 1", (body.name,))
    if existing:
        raise HTTPException(status_code=409, detail=f"Ya existe una bóveda con nombre '{body.name}'")

    row = fetch_one(
        """
        INSERT INTO vaults (name, vault_type, currency, balance, description)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, name, vault_type, currency, balance, description, is_active, created_at
        """,
        (body.name, body.vault_type, body.currency, body.balance, body.description),
    )
    return {"ok": True, "vault": _row(row)}


@router.put("/{vault_id}/adjust")
def adjust_vault(vault_id: int, body: VaultAdjust, auth: dict = Depends(require_admin)):
    """
    Ajusta manualmente el balance de una bóveda.
    Usado para conciliar efectivo real vs saldo en sistema.
    """
    existing = fetch_one("SELECT id, name FROM vaults WHERE id = %s LIMIT 1", (vault_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Bóveda no encontrada")

    row = fetch_one(
        """
        UPDATE vaults
        SET balance = %s,
            description = CASE WHEN %s IS NOT NULL THEN %s ELSE description END,
            updated_at = now()
        WHERE id = %s
        RETURNING id, name, vault_type, currency, balance, updated_at
        """,
        (body.new_balance, body.note, body.note, vault_id),
    )
    logger.info(
        "Vault %s ('%s') balance adjusted to %s by %s",
        vault_id, existing.get("name"), body.new_balance, auth.get("email")
    )
    return {"ok": True, "vault": _row(row)}


@router.get("/provider-liquidation")
def provider_liquidation(auth: dict = Depends(require_admin)):
    """
    Suma los provider_fee_usdt acumulados por proveedor de cuenta.
    Muestra cuánto debe Sendmax a cada proveedor (fees de órdenes cerradas).
    """
    rows = fetch_all(
        """
        SELECT
            u.id AS provider_id,
            COALESCE(u.full_name, u.alias, u.email) AS provider_name,
            COUNT(o.id)                            AS order_count,
            COALESCE(SUM(o.provider_fee_usdt), 0)  AS total_fee_usdt,
            MAX(o.paid_at)                         AS last_order_at
        FROM users u
        JOIN orders o ON o.provider_id = u.id
        WHERE o.status IN ('PAGADA', 'COMPLETADA')
          AND o.provider_fee_usdt > 0
        GROUP BY u.id, u.full_name, u.alias, u.email
        ORDER BY total_fee_usdt DESC
        """
    )
    return {
        "ok": True,
        "providers": [_row(r) for r in (rows or [])],
    }
