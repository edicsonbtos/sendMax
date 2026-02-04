from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from psycopg import Connection


@dataclass
class WithdrawalRow:
    id: int
    user_id: int
    amount_usdt: Decimal
    status: str
    dest_text: str
    proof_file_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    country: Optional[str] = None
    fiat: Optional[str] = None
    fiat_amount: Optional[Decimal] = None
    reject_reason: Optional[str] = None
    resolved_at: Optional[datetime] = None


class WithdrawalsRepo:
    """
    Security rules:
    - user_id is ALWAYS users.id (DB id), never telegram id.
    - create_withdrawal_request_fiat is transactional and enforces balance:
      1) debit wallet (HOLD) with conditional UPDATE (prevents negative / race)
      2) insert ledger entry (WITHDRAWAL_HOLD)
      3) insert withdrawal row (SOLICITADA)
    - reject reverses the hold (credits wallet + ledger reversal)
    """

    def __init__(self, conn: Connection):
        self.conn = conn

    def create_withdrawal_request_fiat(
        self,
        user_id: int,
        amount_usdt: Decimal,
        country: str,
        fiat: str,
        fiat_amount: Decimal,
        dest_text: str,
    ) -> int:
        if amount_usdt <= 0:
            raise ValueError("amount_usdt must be > 0")

        with self.conn.transaction():
            with self.conn.cursor() as cur:
                # Ensure wallet exists
                cur.execute("SELECT 1 FROM wallets WHERE user_id=%s;", (user_id,))
                if not cur.fetchone():
                    cur.execute("INSERT INTO wallets (user_id, balance_usdt) VALUES (%s, 0);", (user_id,))

                # Atomic hold (prevents double-spend / races)
                cur.execute(
                    """
                    UPDATE wallets
                    SET balance_usdt = balance_usdt - %s,
                        updated_at = NOW()
                    WHERE user_id = %s
                      AND balance_usdt >= %s
                    RETURNING balance_usdt
                    """,
                    (amount_usdt, user_id, amount_usdt),
                )
                if not cur.fetchone():
                    raise ValueError("Saldo insuficiente")

                # Create withdrawal
                cur.execute(
                    """
                    INSERT INTO withdrawals (user_id, amount_usdt, status, dest_text, country, fiat, fiat_amount)
                    VALUES (%s, %s, 'SOLICITADA', %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (user_id, amount_usdt, dest_text, country, fiat, fiat_amount),
                )
                (withdrawal_id,) = cur.fetchone()

                # Ledger record for audit
                cur.execute(
                    """
                    INSERT INTO wallet_ledger (user_id, amount_usdt, type, memo)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (user_id, -amount_usdt, "WITHDRAWAL_HOLD", f"withdrawal_id={withdrawal_id}"),
                )

                return int(withdrawal_id)

    def set_withdrawal_resolved(self, withdrawal_id: int, proof_file_id: str) -> None:
        with self.conn.transaction():
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE withdrawals
                    SET status='RESUELTA',
                        proof_file_id=%s,
                        resolved_at=NOW(),
                        updated_at=NOW()
                    WHERE id=%s
                    """,
                    (proof_file_id, withdrawal_id),
                )

    def set_withdrawal_rejected(self, withdrawal_id: int, reject_reason: str) -> None:
        with self.conn.transaction():
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT user_id, amount_usdt, status
                    FROM withdrawals
                    WHERE id=%s
                    """,
                    (withdrawal_id,),
                )
                row = cur.fetchone()
                if not row:
                    raise ValueError("withdrawal not found")

                user_id, amount_usdt, status = row
                if status != "SOLICITADA":
                    raise ValueError("only SOLICITADA can be rejected")

                cur.execute(
                    """
                    UPDATE withdrawals
                    SET status='RECHAZADA',
                        reject_reason=%s,
                        updated_at=NOW()
                    WHERE id=%s
                    """,
                    (reject_reason, withdrawal_id),
                )

                # release hold back to wallet
                cur.execute(
                    """
                    UPDATE wallets
                    SET balance_usdt = balance_usdt + %s,
                        updated_at = NOW()
                    WHERE user_id = %s
                    """,
                    (amount_usdt, user_id),
                )

                cur.execute(
                    """
                    INSERT INTO wallet_ledger (user_id, amount_usdt, type, memo)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (user_id, amount_usdt, "WITHDRAWAL_HOLD_REVERSAL", f"withdrawal_id={withdrawal_id}"),
                )

    def get_withdrawal_by_id(self, withdrawal_id: int) -> Optional[WithdrawalRow]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, user_id, amount_usdt, status, dest_text, proof_file_id,
                       created_at, updated_at, country, fiat, fiat_amount, reject_reason, resolved_at
                FROM withdrawals
                WHERE id=%s
                """,
                (withdrawal_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return WithdrawalRow(*row)

    def list_withdrawals_by_status(self, status: str, limit: int = 50) -> list[WithdrawalRow]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, user_id, amount_usdt, status, dest_text, proof_file_id,
                       created_at, updated_at, country, fiat, fiat_amount, reject_reason, resolved_at
                FROM withdrawals
                WHERE status=%s
                ORDER BY created_at ASC
                LIMIT %s
                """,
                (status, limit),
            )
            return [WithdrawalRow(*r) for r in cur.fetchall()]
