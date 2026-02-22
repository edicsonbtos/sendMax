"""
Repositorio de usuarios.

Aqui concentramos todas las consultas SQL sobre la tabla users.

Changelog:
- telegram_user_id ahora es Optional[int] (nullable en DB).
  Usuarios creados desde backoffice no tienen Telegram.
  IDs negativos sinteticos eliminados; se usa NULL.
- Migracion a ASYNC para Fase 2.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.db.connection import get_async_conn

# --------------------------------------------
# Dataclasses
# --------------------------------------------

@dataclass(frozen=True)
class User:
    id: int
    telegram_user_id: int | None
    alias: str
    role: str
    is_active: bool
    sponsor_id: int | None


@dataclass(frozen=True)
class UserKYC:
    id: int
    telegram_user_id: int | None
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

    email: str | None
    hashed_password: str | None


# --------------------------------------------
# Queries de lectura
# --------------------------------------------

async def get_user_by_telegram_id(telegram_user_id: int) -> User | None:
    """Busca por telegram_user_id real (siempre >0)."""
    if telegram_user_id is None or telegram_user_id <= 0:
        return None
    sql = """
        SELECT id, telegram_user_id, alias, role, is_active, sponsor_id
        FROM users
        WHERE telegram_user_id = %s
        LIMIT 1;
    """
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (telegram_user_id,))
            row = await cur.fetchone()
            return User(*row) if row else None


async def get_user_by_alias(alias: str) -> User | None:
    sql = """
        SELECT id, telegram_user_id, alias, role, is_active, sponsor_id
        FROM users
        WHERE alias = %s
        LIMIT 1;
    """
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (alias,))
            row = await cur.fetchone()
            return User(*row) if row else None


async def get_user_by_id(user_id: int) -> User | None:
    """Busca usuario por ID interno (PK). Util para backoffice."""
    sql = """
        SELECT id, telegram_user_id, alias, role, is_active, sponsor_id
        FROM users
        WHERE id = %s
        LIMIT 1;
    """
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (user_id,))
            row = await cur.fetchone()
            return User(*row) if row else None


async def get_telegram_id_by_user_id(user_id: int) -> int | None:
    """Retorna telegram_user_id o None si el usuario no tiene Telegram."""
    sql = "SELECT telegram_user_id FROM users WHERE id = %s LIMIT 1;"
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (user_id,))
            row = await cur.fetchone()
            if row is None:
                return None
            return int(row[0]) if row[0] is not None else None


async def get_user_kyc_by_telegram_id(telegram_user_id: int) -> UserKYC | None:
    if telegram_user_id is None or telegram_user_id <= 0:
        return None
    sql = """
        SELECT
            id, telegram_user_id, alias, role, is_active, sponsor_id,
            full_name, phone, address_short,
            payout_country, payout_method_text,
            kyc_doc_file_id, kyc_selfie_file_id,
            kyc_status, kyc_submitted_at, kyc_reviewed_at, kyc_review_reason,
            email, hashed_password
        FROM users
        WHERE telegram_user_id = %s
        LIMIT 1;
    """
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (telegram_user_id,))
            row = await cur.fetchone()
            return UserKYC(*row) if row else None


async def get_user_kyc_by_id(user_id: int) -> UserKYC | None:
    """Busca KYC por ID interno. Para backoffice sin telegram_user_id."""
    sql = """
        SELECT
            id, telegram_user_id, alias, role, is_active, sponsor_id,
            full_name, phone, address_short,
            payout_country, payout_method_text,
            kyc_doc_file_id, kyc_selfie_file_id,
            kyc_status, kyc_submitted_at, kyc_reviewed_at, kyc_review_reason,
            email, hashed_password
        FROM users
        WHERE id = %s
        LIMIT 1;
    """
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (user_id,))
            row = await cur.fetchone()
            return UserKYC(*row) if row else None


# --------------------------------------------
# Creacion
# --------------------------------------------

async def create_user(
    telegram_user_id: int | None,
    alias: str,
    sponsor_id: int | None,
    role: str = "operator",
) -> User:
    """Crea usuario. telegram_user_id=None para usuarios de backoffice."""
    sql = """
        INSERT INTO users (telegram_user_id, alias, sponsor_id, role)
        VALUES (%s, %s, %s, %s)
        RETURNING id, telegram_user_id, alias, role, is_active, sponsor_id;
    """
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (telegram_user_id, alias, sponsor_id, role))
            row = await cur.fetchone()
            await conn.commit()
            return User(*row)


# --------------------------------------------
# Email check
# --------------------------------------------

async def check_email_exists(email: str) -> bool:
    """Verifica si un email ya esta registrado (case-insensitive)."""
    sql = "SELECT EXISTS(SELECT 1 FROM users WHERE LOWER(email) = LOWER(%s));"
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (email,))
            row = await cur.fetchone()
            return bool(row[0]) if row else False


# --------------------------------------------
# KYC
# --------------------------------------------

async def submit_kyc(
    *,
    telegram_user_id: int,
    full_name: str,
    phone: str,
    address_short: str,
    payout_country: str,
    payout_method_text: str,
    kyc_doc_file_id: str,
    kyc_selfie_file_id: str,
    email: str,
    hashed_password: str,
) -> bool:
    """
    Guarda KYC completo y deja status=SUBMITTED.
    Solo se llama desde Telegram, telegram_user_id siempre es int real.
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
            email=%s,
            hashed_password=%s,
            kyc_status='SUBMITTED',
            kyc_submitted_at=now(),
            updated_at=now()
        WHERE telegram_user_id=%s;
    """
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                sql,
                (
                    full_name, phone, address_short,
                    payout_country, payout_method_text,
                    kyc_doc_file_id, kyc_selfie_file_id,
                    email, hashed_password,
                    telegram_user_id,
                ),
            )
            ok = cur.rowcount > 0
            await conn.commit()
            return ok


async def set_kyc_status(
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
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (new_status, reason, user_id))
            ok = cur.rowcount > 0
            await conn.commit()
            return ok


# --------------------------------------------
# Payout
# --------------------------------------------

async def set_payout_method(
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
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (payout_country, payout_method_text, user_id))
            ok = cur.rowcount > 0
            await conn.commit()
            return ok


async def get_payout_method(user_id: int) -> tuple[str | None, str | None]:
    sql = "SELECT payout_country, payout_method_text FROM users WHERE id=%s LIMIT 1;"
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (user_id,))
            row = await cur.fetchone()
            if not row:
                return (None, None)
            return (row[0], row[1])


# --------------------------------------------
# KYC draft (progreso parcial desde Telegram)
# --------------------------------------------

async def update_kyc_draft(
    *,
    telegram_user_id: int,
    full_name: str | None = None,
    phone: str | None = None,
    address_short: str | None = None,
    payout_country: str | None = None,
    payout_method_text: str | None = None,
    kyc_doc_file_id: str | None = None,
    kyc_selfie_file_id: str | None = None,
    email: str | None = None,
    hashed_password: str | None = None,
) -> bool:
    """
    Guarda progreso parcial del KYC sin marcar SUBMITTED.
    Solo se llama desde Telegram, telegram_user_id es siempre int real.
    """
    if telegram_user_id is None:
        raise ValueError("update_kyc_draft requiere telegram_user_id real")

    fields = []
    params: list = []

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
    if email is not None:
        add("email", email)
    if hashed_password is not None:
        add("hashed_password", hashed_password)

    if not fields:
        return False

    sql = f"""
        UPDATE users
        SET {", ".join(fields)},
            updated_at=now()
        WHERE telegram_user_id=%s;
    """
    params.append(int(telegram_user_id))

    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, tuple(params))
            ok = cur.rowcount > 0
            await conn.commit()
            return ok
