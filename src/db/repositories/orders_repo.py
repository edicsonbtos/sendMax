"""
Repositorio de ordenes (orders).

MVP:
- Crear orden (CREADA) con snapshot de tasa y comprobante origen.
- public_id consecutivo robusto con SEQUENCE.

Operacion Admin:
- Listar / buscar / actualizar status
- Marcar PAGADA con comprobante destino (foto) + paid_at
- Cancelar con motivo (cancel_reason)
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from src.db.connection import get_conn


@dataclass(frozen=True)
class Order:
    id: int
    public_id: int
    operator_user_id: int
    origin_country: str
    dest_country: str
    amount_origin: Decimal
    rate_version_id: int
    commission_pct: Decimal
    rate_client: Decimal
    payout_dest: Decimal
    beneficiary_text: str
    origin_payment_proof_file_id: str
    status: str
    dest_payment_proof_file_id: str | None = None
    paid_at: object | None = None
    cancel_reason: str | None = None


VALID_STATUSES = {"CREADA", "ORIGEN_VERIFICANDO", "ORIGEN_CONFIRMADO", "EN_PROCESO", "PAGADA", "CANCELADA"}

VALID_TRANSITIONS = {
    "CREADA":             {"ORIGEN_VERIFICANDO", "CANCELADA"},
    "ORIGEN_VERIFICANDO": {"ORIGEN_CONFIRMADO", "CANCELADA"},
    "ORIGEN_CONFIRMADO":  {"EN_PROCESO", "CANCELADA"},
    "EN_PROCESO":         {"PAGADA", "CANCELADA"},
    "PAGADA":             set(),
    "CANCELADA":          set(),
}


def next_public_id(cur) -> int:
    cur.execute("SELECT nextval('orders_public_id_seq');")
    (val,) = cur.fetchone()
    return int(val)


def create_order(
    *,
    operator_user_id: int,
    origin_country: str,
    dest_country: str,
    amount_origin: Decimal,
    rate_version_id: int,
    commission_pct: Decimal,
    rate_client: Decimal,
    payout_dest: Decimal,
    beneficiary_text: str,
    origin_payment_proof_file_id: str,
) -> Order:
    sql_insert = """
        INSERT INTO orders (
            public_id, operator_user_id,
            origin_country, dest_country,
            amount_origin,
            rate_version_id, commission_pct, rate_client, payout_dest,
            beneficiary_text,
            origin_payment_proof_file_id,
            status
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'CREADA')
        RETURNING
            id, public_id, operator_user_id,
            origin_country, dest_country,
            amount_origin,
            rate_version_id, commission_pct, rate_client, payout_dest,
            beneficiary_text,
            origin_payment_proof_file_id,
            status,
            dest_payment_proof_file_id,
            paid_at,
            cancel_reason;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            public_id = next_public_id(cur)
            cur.execute(
                sql_insert,
                (
                    public_id, operator_user_id,
                    origin_country, dest_country,
                    amount_origin,
                    rate_version_id, commission_pct, rate_client, payout_dest,
                    beneficiary_text,
                    origin_payment_proof_file_id,
                ),
            )
            row = cur.fetchone()
            conn.commit()
            return Order(*row)


def get_order_by_public_id(public_id: int) -> Optional[Order]:
    sql = """
        SELECT
            id, public_id, operator_user_id,
            origin_country, dest_country,
            amount_origin,
            rate_version_id, commission_pct, rate_client, payout_dest,
            beneficiary_text,
            origin_payment_proof_file_id,
            status,
            dest_payment_proof_file_id,
            paid_at,
            cancel_reason
        FROM orders
        WHERE public_id = %s
        LIMIT 1;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (public_id,))
            row = cur.fetchone()
            return Order(*row) if row else None


def list_orders_by_status(status: str, limit: int = 10) -> list[Order]:
    if status not in VALID_STATUSES:
        raise ValueError(f"Estado invalido: {status}")
    sql = """
        SELECT
            id, public_id, operator_user_id,
            origin_country, dest_country,
            amount_origin,
            rate_version_id, commission_pct, rate_client, payout_dest,
            beneficiary_text,
            origin_payment_proof_file_id,
            status,
            dest_payment_proof_file_id,
            paid_at,
            cancel_reason
        FROM orders
        WHERE status = %s
        ORDER BY created_at ASC
        LIMIT %s;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (status, limit))
            rows = cur.fetchall()
            return [Order(*r) for r in rows]


def update_order_status(public_id: int, new_status: str) -> bool:
    if new_status not in VALID_STATUSES:
        raise ValueError(f"Estado invalido: {new_status}")

    allowed_from = [st for st, targets in VALID_TRANSITIONS.items() if new_status in targets]
    if not allowed_from:
        raise ValueError(f"No hay transicion valida hacia {new_status}")

    placeholders = ",".join(["%s"] * len(allowed_from))
    sql = f"""
        UPDATE orders
        SET status = %s, updated_at = now()
        WHERE public_id = %s
          AND status IN ({placeholders});
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (new_status, public_id) + tuple(allowed_from))
            updated = cur.rowcount > 0
            conn.commit()
            return updated


def mark_origin_verified(public_id: int, *, by_telegram_user_id: int | None = None, by_name: str | None = None) -> bool:
    sql = """
        UPDATE orders
        SET
            status = 'ORIGEN_CONFIRMADO',
            origin_verified_at = now(),
            origin_verified_by_telegram_id = %s,
            origin_verified_by_name = %s,
            updated_at = now()
        WHERE public_id = %s
          AND status IN ('CREADA', 'ORIGEN_VERIFICANDO');
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (by_telegram_user_id, by_name, public_id))
            ok = cur.rowcount > 0
            conn.commit()
            return ok


def mark_order_paid(public_id: int, dest_payment_proof_file_id: str) -> bool:
    sql = """
        UPDATE orders
        SET
            status = 'PAGADA',
            dest_payment_proof_file_id = %s,
            paid_at = now(),
            updated_at = now()
        WHERE public_id = %s
          AND status = 'EN_PROCESO';
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (dest_payment_proof_file_id, public_id))
            ok = cur.rowcount > 0
            conn.commit()
            return ok


def cancel_order(public_id: int, reason: str) -> bool:
    sql = """
        UPDATE orders
        SET
            status = 'CANCELADA',
            cancel_reason = %s,
            updated_at = now()
        WHERE public_id = %s
          AND status NOT IN ('PAGADA', 'CANCELADA');
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (reason, public_id))
            ok = cur.rowcount > 0
            conn.commit()
            return ok


def set_profit_usdt(public_id: int, profit_usdt: Decimal) -> bool:
    sql = """
        UPDATE orders
        SET profit_usdt = %s, updated_at = now()
        WHERE public_id = %s;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (profit_usdt, public_id))
            ok = cur.rowcount > 0
            conn.commit()
            return ok


def set_awaiting_paid_proof(public_id: int, *, by_telegram_user_id: int | None = None) -> bool:
    sql = """
        UPDATE orders
        SET awaiting_paid_proof = true,
            awaiting_paid_proof_at = now(),
            awaiting_paid_proof_by = %s,
            updated_at = now()
        WHERE public_id = %s;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (by_telegram_user_id, public_id))
            ok = cur.rowcount > 0
            conn.commit()
            return ok


def clear_awaiting_paid_proof(public_id: int) -> bool:
    sql = """
        UPDATE orders
        SET awaiting_paid_proof = false,
            awaiting_paid_proof_at = NULL,
            awaiting_paid_proof_by = NULL,
            updated_at = now()
        WHERE public_id = %s;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (public_id,))
            ok = cur.rowcount > 0
            conn.commit()
            return ok


def list_orders_awaiting_paid_proof(limit: int = 10) -> list[Order]:
    sql = """
        SELECT
            id, public_id, operator_user_id,
            origin_country, dest_country,
            amount_origin,
            rate_version_id, commission_pct, rate_client, payout_dest,
            beneficiary_text,
            origin_payment_proof_file_id,
            status,
            dest_payment_proof_file_id,
            paid_at,
            cancel_reason
        FROM orders
        WHERE awaiting_paid_proof = true
        ORDER BY awaiting_paid_proof_at ASC NULLS LAST
        LIMIT %s;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (limit,))
            rows = cur.fetchall()
            return [Order(*r) for r in rows]


def list_orders_awaiting_paid_proof_by(by_telegram_user_id: int, limit: int = 10) -> list[Order]:
    sql = """
        SELECT
            id, public_id, operator_user_id,
            origin_country, dest_country,
            amount_origin,
            rate_version_id, commission_pct, rate_client, payout_dest,
            beneficiary_text,
            origin_payment_proof_file_id,
            status,
            dest_payment_proof_file_id,
            paid_at,
            cancel_reason
        FROM orders
        WHERE awaiting_paid_proof = true
          AND awaiting_paid_proof_by = %s
        ORDER BY awaiting_paid_proof_at ASC NULLS LAST
        LIMIT %s;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (by_telegram_user_id, limit))
            rows = cur.fetchall()
            return [Order(*r) for r in rows]


def mark_order_paid_tx(conn, public_id: int, dest_payment_proof_file_id: str) -> bool:
    sql = """
        UPDATE orders
        SET
            status = 'PAGADA',
            dest_payment_proof_file_id = %s,
            paid_at = now(),
            updated_at = now()
        WHERE public_id = %s
          AND status = 'EN_PROCESO';
    """
    with conn.cursor() as cur:
        cur.execute(sql, (dest_payment_proof_file_id, public_id))
        return cur.rowcount > 0


def set_profit_usdt_tx(conn, public_id: int, profit_usdt: Decimal) -> bool:
    sql = """
        UPDATE orders
        SET profit_usdt = %s, updated_at = now()
        WHERE public_id = %s;
    """
    with conn.cursor() as cur:
        cur.execute(sql, (profit_usdt, public_id))
        return cur.rowcount > 0


def clear_awaiting_paid_proof_tx(conn, public_id: int) -> bool:
    sql = """
        UPDATE orders
        SET awaiting_paid_proof = false,
            awaiting_paid_proof_at = NULL,
            awaiting_paid_proof_by = NULL,
            updated_at = now()
        WHERE public_id = %s;
    """
    with conn.cursor() as cur:
        cur.execute(sql, (public_id,))
        return cur.rowcount > 0