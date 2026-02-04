from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import psycopg

from src.config.settings import settings


@dataclass(frozen=True)
class Wallet:
    user_id: int
    balance_usdt: Decimal


def get_conn():
    return psycopg.connect(settings.DATABASE_URL)


def get_or_create_wallet(user_id: int) -> Wallet:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id, balance_usdt FROM wallets WHERE user_id = %s LIMIT 1;", (user_id,))
            row = cur.fetchone()
            if row:
                return Wallet(int(row[0]), Decimal(str(row[1])))

            cur.execute(
                "INSERT INTO wallets (user_id, balance_usdt) VALUES (%s, 0) RETURNING user_id, balance_usdt;",
                (user_id,),
            )
            row = cur.fetchone()
            conn.commit()
            return Wallet(int(row[0]), Decimal(str(row[1])))


def get_balance(user_id: int) -> Decimal:
    return get_or_create_wallet(user_id).balance_usdt


def add_ledger_entry(
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
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Asegura wallet
            cur.execute("SELECT 1 FROM wallets WHERE user_id=%s;", (user_id,))
            if not cur.fetchone():
                cur.execute("INSERT INTO wallets (user_id, balance_usdt) VALUES (%s, 0);", (user_id,))

            if idempotency and ref_order_public_id is not None:
                # Chequeo idempotente (MVP seguro) sin migraciones:
                # "si ya existe un ledger con mismo user_id + type + ref_order_public_id + amount_usdt, no repitas".
                cur.execute(
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
                if cur.fetchone():
                    # Ya aplicado: no tocar balance de nuevo.
                    conn.commit()
                    return

            # Ledger (audit)
            cur.execute(
                """
                INSERT INTO wallet_ledger (user_id, amount_usdt, type, ref_order_public_id, memo)
                VALUES (%s, %s, %s, %s, %s);
                """,
                (user_id, amount_usdt, entry_type, ref_order_public_id, memo),
            )

            # Wallet (saldo materializado)
            cur.execute(
                """
                UPDATE wallets
                SET balance_usdt = balance_usdt + %s,
                    updated_at = now()
                WHERE user_id = %s;
                """,
                (amount_usdt, user_id),
            )
        conn.commit()


def create_withdrawal_request(*, user_id: int, amount_usdt: Decimal, dest_text: str) -> int:
    """
    Crea una solicitud de retiro simple (status=SOLICITADA).
    NOTA: tu flujo principal usa WithdrawalsRepo.create_withdrawal_request_fiat()
    que hace HOLD atómico. Esta función se mantiene por compatibilidad.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            # asegura wallet
            cur.execute("SELECT 1 FROM wallets WHERE user_id=%s;", (user_id,))
            if not cur.fetchone():
                cur.execute("INSERT INTO wallets (user_id, balance_usdt) VALUES (%s, 0);", (user_id,))

            cur.execute(
                """
                INSERT INTO withdrawals (user_id, amount_usdt, status, dest_text)
                VALUES (%s, %s, 'SOLICITADA', %s)
                RETURNING id;
                """,
                (user_id, amount_usdt, dest_text),
            )
            (wid,) = cur.fetchone()
        conn.commit()
        return int(wid)


def add_ledger_entry_tx(
    conn,
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
    with conn.cursor() as cur:
        # Asegura wallet
        cur.execute("SELECT 1 FROM wallets WHERE user_id=%s;", (user_id,))
        if not cur.fetchone():
            cur.execute("INSERT INTO wallets (user_id, balance_usdt) VALUES (%s, 0);", (user_id,))

        if idempotency and ref_order_public_id is not None:
            cur.execute(
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
            if cur.fetchone():
                return

        # Ledger (audit)
        cur.execute(
            """
            INSERT INTO wallet_ledger (user_id, amount_usdt, type, ref_order_public_id, memo)
            VALUES (%s, %s, %s, %s, %s);
            """,
            (user_id, amount_usdt, entry_type, ref_order_public_id, memo),
        )

        # Wallet (saldo materializado)
        cur.execute(
            """
            UPDATE wallets
            SET balance_usdt = balance_usdt + %s,
                updated_at = now()
            WHERE user_id = %s;
            """,
            (amount_usdt, user_id),
        )
