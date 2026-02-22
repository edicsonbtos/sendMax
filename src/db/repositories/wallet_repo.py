from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import psycopg

from src.db.connection import get_async_conn


@dataclass(frozen=True)
class Wallet:
    user_id: int
    balance_usdt: Decimal


async def get_or_create_wallet(user_id: int) -> Wallet:
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO wallets (user_id, balance_usdt)
                VALUES (%s, 0)
                ON CONFLICT (user_id) DO NOTHING;
                """,
                (user_id,),
            )
            await cur.execute("SELECT user_id, balance_usdt FROM wallets WHERE user_id = %s LIMIT 1;", (user_id,))
            row = await cur.fetchone()
            await conn.commit()
            if not row:
                raise RuntimeError(f"No se pudo obtener/crear wallet para user_id={user_id}")
            return Wallet(int(row[0]), Decimal(str(row[1])))


async def get_balance(user_id: int) -> Decimal:
    w = await get_or_create_wallet(user_id)
    return w.balance_usdt


async def add_ledger_entry(
    *,
    user_id: int,
    amount_usdt: Decimal,
    entry_type: str,
    ref_order_public_id: int | None = None,
    memo: str | None = None,
    # Compatibilidad con el código existente (admin_orders.py):
    idempotency: bool = False,
) -> None:
    """
    Inserta un movimiento en wallet_ledger y aplica el delta a wallets.balance_usdt.

    Seguridad:
    - Si idempotency=True, evita duplicar el mismo crédito/débito para la misma orden
      y tipo de movimiento (ej: ORDER_PROFIT para ref_order_public_id=123).
      Esto protege contra reintentos del admin/bot.
    """
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            # Asegura wallet de forma atómica
            await cur.execute(
                "INSERT INTO wallets (user_id, balance_usdt) VALUES (%s, 0) ON CONFLICT (user_id) DO NOTHING;",
                (user_id,),
            )

            if idempotency and ref_order_public_id is not None:
                # Chequeo idempotente (MVP seguro) sin migraciones:
                # "si ya existe un ledger con mismo user_id + type + ref_order_public_id + amount_usdt, no repitas".
                await cur.execute(
                    """
                    SELECT 1
                    FROM wallet_ledger
                    WHERE user_id=%s
                      AND type=%s
                      AND ref_order_public_id=%s
                      AND amount_usdt=%s
                    LIMIT 1
                    """,
                    (user_id, entry_type, ref_order_public_id, amount_usdt),
                )
                res_idemp = await cur.fetchone()
                if res_idemp:
                    # Ya aplicado: no tocar balance de nuevo.
                    await conn.commit()
                    return

            # Ledger (audit) con idempotencia fuerte
            await cur.execute(
                """
                INSERT INTO wallet_ledger (user_id, amount_usdt, type, ref_order_public_id, memo)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (user_id, type, ref_order_public_id) WHERE ref_order_public_id IS NOT NULL DO NOTHING
                RETURNING id;
                """,
                (user_id, amount_usdt, entry_type, ref_order_public_id, memo),
            )
            res_ledger = await cur.fetchone()
            inserted = bool(res_ledger)

            # Wallet (saldo materializado) solo si se insertó el ledger
            if inserted:
                await cur.execute(
                    """
                    UPDATE wallets
                    SET balance_usdt = balance_usdt + %s,
                        updated_at = now()
                    WHERE user_id = %s;
                    """,
                    (amount_usdt, user_id),
                )
        await conn.commit()


async def create_withdrawal_request(*, user_id: int, amount_usdt: Decimal, dest_text: str) -> int:
    """
    Crea una solicitud de retiro simple (status=SOLICITADA).
    NOTA: tu flujo principal usa WithdrawalsRepo.create_withdrawal_request_fiat()
    que hace HOLD atómico. Esta función se mantiene por compatibilidad.
    """
    async with get_async_conn() as conn:
        async with conn.cursor() as cur:
            # asegura wallet de forma atómica
            await cur.execute(
                "INSERT INTO wallets (user_id, balance_usdt) VALUES (%s, 0) ON CONFLICT (user_id) DO NOTHING;",
                (user_id,),
            )

            await cur.execute(
                """
                INSERT INTO withdrawals (user_id, amount_usdt, status, dest_text)
                VALUES (%s, %s, 'SOLICITADA', %s)
                RETURNING id;
                """,
                (user_id, amount_usdt, dest_text),
            )
            res_wid = await cur.fetchone()
            wid = res_wid[0] if res_wid else 0
        await conn.commit()
        return int(wid)


async def add_ledger_entry_tx(
    conn: psycopg.AsyncConnection,
    *,
    user_id: int,
    amount_usdt: Decimal,
    entry_type: str,
    ref_order_public_id: int | None = None,
    memo: str | None = None,
    idempotency: bool = False,
) -> None:
    """
    Igual que add_ledger_entry, pero usando la conexión/transacción existente.
    NO hace commit. Ideal para cierres atómicos.
    """
    async with conn.cursor() as cur:
        # Asegura wallet de forma atómica
        await cur.execute(
            "INSERT INTO wallets (user_id, balance_usdt) VALUES (%s, 0) ON CONFLICT (user_id) DO NOTHING;",
            (user_id,),
        )

        if idempotency and ref_order_public_id is not None:
            await cur.execute(
                """
                SELECT 1
                FROM wallet_ledger
                WHERE user_id=%s
                  AND type=%s
                  AND ref_order_public_id=%s
                  AND amount_usdt=%s
                LIMIT 1
                """,
                (user_id, entry_type, ref_order_public_id, amount_usdt),
            )
            res_idemp = await cur.fetchone()
            if res_idemp:
                return

        # Ledger (audit) con idempotencia fuerte
        await cur.execute(
            """
            INSERT INTO wallet_ledger (user_id, amount_usdt, type, ref_order_public_id, memo)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (user_id, type, ref_order_public_id) WHERE ref_order_public_id IS NOT NULL DO NOTHING
            RETURNING id;
            """,
            (user_id, amount_usdt, entry_type, ref_order_public_id, memo),
        )
        res_ledger = await cur.fetchone()
        inserted_ledger = bool(res_ledger)

        # Wallet (saldo materializado) solo si se insertó el ledger
        if inserted_ledger:
            await cur.execute(
                """
                UPDATE wallets
                SET balance_usdt = balance_usdt + %s,
                    updated_at = now()
                WHERE user_id = %s;
                """,
                (amount_usdt, user_id),
            )
