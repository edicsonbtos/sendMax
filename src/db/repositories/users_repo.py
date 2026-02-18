"""
Repositorio de usuarios.

Aquí concentramos todas las consultas SQL sobre la tabla users.
"""

from __future__ import annotations
from src.db.connection import get_conn

from dataclasses import dataclass



@dataclass(frozen=True)
class User:
    id: int
    telegram_user_id: int
    alias: str
    role: str
    is_active: bool
    sponsor_id: int | None


@dataclass(frozen=True)
class UserKYC:
    id: int
    telegram_user_id: int
    alias: str
    role: str
    is_active: bool
    sponsor_id: int | None

    full_name: str | None
    phone: str | None
    address_short: str | None

    payout_country: str | None
    payout_method_text: str | None

    kyc_doc_file_id: str | None
    kyc_selfie_file_id: str | None
    kyc_status: str
    kyc_submitted_at: object | None
    kyc_reviewed_at: object | None
    kyc_review_reason: str | None


# get_conn importado desde connection.py (pool centralizado)


def get_user_by_telegram_id(telegram_user_id: int) -> User | None:
    sql = """
        SELECT id, telegram_user_id, alias, role, is_active, sponsor_id
        FROM users
        WHERE telegram_user_id = %s
        LIMIT 1;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (telegram_user_id,))
            row = cur.fetchone()
            return User(*row) if row else None


def get_user_by_alias(alias: str) -> User | None:
    # alias es CITEXT en DB, búsqueda case-insensitive.
    sql = """
        SELECT id, telegram_user_id, alias, role, is_active, sponsor_id
        FROM users
        WHERE alias = %s
        LIMIT 1;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (alias,))
            row = cur.fetchone()
            return User(*row) if row else None


def get_telegram_id_by_user_id(user_id: int) -> int | None:
    sql = "SELECT telegram_user_id FROM users WHERE id = %s LIMIT 1;"
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            row = cur.fetchone()
            return int(row[0]) if row else None


def create_user(
    telegram_user_id: int,
    alias: str,
    sponsor_id: int | None,
    role: str = "operator",
) -> User:
    sql = """
        INSERT INTO users (telegram_user_id, alias, sponsor_id, role)
        VALUES (%s, %s, %s, %s)
        RETURNING id, telegram_user_id, alias, role, is_active, sponsor_id;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (telegram_user_id, alias, sponsor_id, role))
            row = cur.fetchone()
            conn.commit()
            return User(*row)


# --- KYC + payout ---

def get_user_kyc_by_telegram_id(telegram_user_id: int) -> UserKYC | None:
    sql = """
        SELECT
            id, telegram_user_id, alias, role, is_active, sponsor_id,
            full_name, phone, address_short,
            payout_country, payout_method_text,
            kyc_doc_file_id, kyc_selfie_file_id,
            kyc_status, kyc_submitted_at, kyc_reviewed_at, kyc_review_reason
        FROM users
        WHERE telegram_user_id = %s
        LIMIT 1;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (telegram_user_id,))
            row = cur.fetchone()
            return UserKYC(*row) if row else None


def submit_kyc(
    *,
    telegram_user_id: int,
    full_name: str,
    phone: str,
    address_short: str,
    payout_country: str,
    payout_method_text: str,
    kyc_doc_file_id: str,
    kyc_selfie_file_id: str,
) -> bool:
    """
    Guarda KYC y deja status=SUBMITTED. (Aprobación es manual por admin)
    """
    sql = """
        UPDATE users
        SET
            full_name=%s,
            phone=%s,
            address_short=%s,
            payout_country=%s,
            payout_method_text=%s,
            kyc_doc_file_id=%s,
            kyc_selfie_file_id=%s,
            kyc_status='SUBMITTED',
            kyc_submitted_at=now(),
            updated_at=now()
        WHERE telegram_user_id=%s;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    full_name, phone, address_short,
                    payout_country, payout_method_text,
                    kyc_doc_file_id, kyc_selfie_file_id,
                    telegram_user_id,
                ),
            )
            ok = cur.rowcount > 0
            conn.commit()
            return ok


def set_kyc_status(
    *,
    user_id: int,
    new_status: str,
    reason: str | None = None,
) -> bool:
    """
    new_status: APPROVED / REJECTED / PENDING / SUBMITTED
    """
    sql = """
        UPDATE users
        SET
            kyc_status=%s,
            kyc_review_reason=%s,
            kyc_reviewed_at=now(),
            updated_at=now()
        WHERE id=%s;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (new_status, reason, user_id))
            ok = cur.rowcount > 0
            conn.commit()
            return ok


def set_payout_method(
    *,
    user_id: int,
    payout_country: str,
    payout_method_text: str,
) -> bool:
    sql = """
        UPDATE users
        SET payout_country=%s,
            payout_method_text=%s,
            updated_at=now()
        WHERE id=%s;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (payout_country, payout_method_text, user_id))
            ok = cur.rowcount > 0
            conn.commit()
            return ok


def get_payout_method(user_id: int) -> tuple[str | None, str | None]:
    sql = "SELECT payout_country, payout_method_text FROM users WHERE id=%s LIMIT 1;"
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            row = cur.fetchone()
            if not row:
                return (None, None)
            return (row[0], row[1])

def update_kyc_draft(
    *,
    telegram_user_id: int,
    full_name: str | None = None,
    phone: str | None = None,
    address_short: str | None = None,
    payout_country: str | None = None,
    payout_method_text: str | None = None,
    kyc_doc_file_id: str | None = None,
    kyc_selfie_file_id: str | None = None,
) -> bool:
    """
    Guarda progreso parcial del KYC sin marcar SUBMITTED.
    Solo actualiza campos que vengan != None.
    """
    fields = []
    params = []

    def add(col: str, val):
        fields.append(f"{col}=%s")
        params.append(val)

    if full_name is not None:
        add("full_name", full_name)
    if phone is not None:
        add("phone", phone)
    if address_short is not None:
        add("address_short", address_short)
    if payout_country is not None:
        add("payout_country", payout_country)
    if payout_method_text is not None:
        add("payout_method_text", payout_method_text)
    if kyc_doc_file_id is not None:
        add("kyc_doc_file_id", kyc_doc_file_id)
    if kyc_selfie_file_id is not None:
        add("kyc_selfie_file_id", kyc_selfie_file_id)

    if not fields:
        return False

    # No cambiamos status aquí, solo guardamos draft.
    sql = f"""
        UPDATE users
        SET {", ".join(fields)},
            updated_at=now()
        WHERE telegram_user_id=%s;
    """
    params.append(int(telegram_user_id))

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params))
            ok = cur.rowcount > 0
            conn.commit()
            return ok
