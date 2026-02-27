"""
Repositorio: Agenda de Contactos del Operador (saved_beneficiaries).

Diseño de inmutabilidad:
  - Nunca se hace UPDATE sobre un registro existente.
  - Al "editar", se crea un nuevo registro y el anterior
    queda con is_active=false + superseded_by=new_id.
  - Las órdenes guardan beneficiary_id como snapshot permanente.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from src.db.connection import get_async_conn

logger = logging.getLogger(__name__)


class SavedBeneficiary:
    __slots__ = (
        "id", "user_id", "alias", "full_name", "id_number",
        "bank_name", "account_number", "phone",
        "dest_country", "payment_method", "notes",
        "is_active", "times_used",
    )

    def __init__(self, row: dict[str, Any]) -> None:
        self.id: int = row["id"]
        self.user_id: int = row["user_id"]
        self.alias: str = row["alias"]
        self.full_name: Optional[str] = row.get("full_name")
        self.id_number: Optional[str] = row.get("id_number")
        self.bank_name: Optional[str] = row.get("bank_name")
        self.account_number: Optional[str] = row.get("account_number")
        self.phone: Optional[str] = row.get("phone")
        self.dest_country: str = row["dest_country"]
        self.payment_method: Optional[str] = row.get("payment_method")
        self.notes: Optional[str] = row.get("notes")
        self.is_active: bool = bool(row.get("is_active", True))
        self.times_used: int = int(row.get("times_used", 0))


async def list_active(user_id: int, dest_country: Optional[str] = None) -> list[SavedBeneficiary]:
    """Devuelve los contactos activos del operador, opcionalmente filtrados por país destino."""
    if dest_country:
        sql = """
            SELECT id, user_id, alias, full_name, id_number,
                   bank_name, account_number, phone,
                   dest_country, payment_method, notes,
                   is_active, times_used
            FROM saved_beneficiaries
            WHERE user_id = %s AND dest_country = %s AND is_active = true
            ORDER BY times_used DESC, alias ASC
            LIMIT 20;
        """
        params: tuple = (user_id, dest_country)
    else:
        sql = """
            SELECT id, user_id, alias, full_name, id_number,
                   bank_name, account_number, phone,
                   dest_country, payment_method, notes,
                   is_active, times_used
            FROM saved_beneficiaries
            WHERE user_id = %s AND is_active = true
            ORDER BY times_used DESC, alias ASC
            LIMIT 20;
        """
        params = (user_id,)

    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, params)
            cols = [d[0] for d in cur.description]
            rows = await cur.fetchall()
            return [SavedBeneficiary(dict(zip(cols, r))) for r in rows]


async def get_by_id(beneficiary_id: int) -> Optional[SavedBeneficiary]:
    """Obtiene un beneficiario por su ID (incluye inactivos para historial)."""
    sql = """
        SELECT id, user_id, alias, full_name, id_number,
               bank_name, account_number, phone,
               dest_country, payment_method, notes,
               is_active, times_used
        FROM saved_beneficiaries WHERE id = %s LIMIT 1;
    """
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (beneficiary_id,))
            cols = [d[0] for d in cur.description]
            row = await cur.fetchone()
            return SavedBeneficiary(dict(zip(cols, row))) if row else None


async def save(
    *,
    user_id: int,
    alias: str,
    dest_country: str,
    full_name: Optional[str] = None,
    id_number: Optional[str] = None,
    bank_name: Optional[str] = None,
    account_number: Optional[str] = None,
    phone: Optional[str] = None,
    payment_method: Optional[str] = None,
    notes: Optional[str] = None,
) -> SavedBeneficiary:
    """
    Crea un nuevo beneficiario activo.
    Si existe uno activo con el mismo alias+dest_country,
    lo desactiva primero (cadena de versiones inmutable).
    """
    async with get_async_conn() as conn:
        async with conn.transaction():
            async with conn.cursor() as cur:
                # 1. Desactivar versión previa con mismo alias
                await cur.execute(
                    """
                    UPDATE saved_beneficiaries
                    SET is_active = false, updated_at = now()
                    WHERE user_id = %s AND alias = %s AND dest_country = %s AND is_active = true;
                    """,
                    (user_id, alias, dest_country),
                )

                # 2. Crear nuevo registro activo
                await cur.execute(
                    """
                    INSERT INTO saved_beneficiaries
                        (user_id, alias, full_name, id_number,
                         bank_name, account_number, phone,
                         dest_country, payment_method, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, user_id, alias, full_name, id_number,
                              bank_name, account_number, phone,
                              dest_country, payment_method, notes,
                              is_active, times_used;
                    """,
                    (user_id, alias, full_name, id_number,
                     bank_name, account_number, phone,
                     dest_country, payment_method, notes),
                )
                cols = [d[0] for d in cur.description]
                row = await cur.fetchone()
                if not row:
                    raise RuntimeError("save_beneficiary: INSERT returned no row")
                return SavedBeneficiary(dict(zip(cols, row)))


async def increment_uses(beneficiary_id: int) -> None:
    """Incrementa el contador de usos atómicamente."""
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE saved_beneficiaries SET times_used = times_used + 1, updated_at = now() WHERE id = %s;",
                (beneficiary_id,),
            )
            await conn.commit()


async def link_order_to_beneficiary(public_id: int, beneficiary_id: int) -> None:
    """Guarda el snapshot del beneficiario usado en la orden (beneficiary_id = FK inmutable)."""
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE orders SET beneficiary_id = %s WHERE public_id = %s;",
                (beneficiary_id, public_id),
            )
            await conn.commit()


async def mark_smart_save_pending(public_id: int) -> None:
    """Marca que la orden fue creada manualmente y aún no se decidió guardar el contacto."""
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE orders SET smart_save_pending = true WHERE public_id = %s;",
                (public_id,),
            )
            await conn.commit()
