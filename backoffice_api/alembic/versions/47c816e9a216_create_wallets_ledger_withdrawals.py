"""create wallets ledger withdrawals

Revision ID: 47c816e9a216
Revises: c525e594bdd5
Create Date: 2026-01-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "47c816e9a216"
down_revision: Union[str, Sequence[str], None] = "c525e594bdd5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Wallets (saldo USDT por usuario)
    op.create_table(
        "wallets",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("balance_usdt", sa.Numeric(18, 8), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_foreign_key(
        "fk_wallets_user",
        "wallets",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 2) Ledger append-only (auditoría)
    op.create_table(
        "wallet_ledger",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),

        # + crédito / - débito
        sa.Column("amount_usdt", sa.Numeric(18, 8), nullable=False),

        # Tipos: ORDER_PROFIT, SPONSOR_COMMISSION, WITHDRAWAL, ADJUSTMENT, REVERSAL, etc.
        sa.Column("type", sa.Text(), nullable=False),

        # Referencia humana a la orden (public_id)
        sa.Column("ref_order_public_id", sa.BigInteger(), nullable=True),

        # Nota libre (por ejemplo motivo ajuste/cancelación)
        sa.Column("memo", sa.Text(), nullable=True),

        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_foreign_key(
        "fk_wallet_ledger_user",
        "wallet_ledger",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_wallet_ledger_user", "wallet_ledger", ["user_id"])
    op.create_index("ix_wallet_ledger_type", "wallet_ledger", ["type"])
    op.create_index("ix_wallet_ledger_order", "wallet_ledger", ["ref_order_public_id"])

    # 3) Withdrawals (solicitudes de retiro)
    op.create_table(
        "withdrawals",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),

        sa.Column("amount_usdt", sa.Numeric(18, 8), nullable=False),

        # Estado: SOLICITADA / RESUELTA / RECHAZADA
        sa.Column("status", sa.Text(), nullable=False, server_default="SOLICITADA"),

        # A dónde se pagó (texto: dirección USDT / banco / etc.)
        sa.Column("dest_text", sa.Text(), nullable=False),

        # Comprobante del admin (file_id telegram) al resolver
        sa.Column("proof_file_id", sa.Text(), nullable=True),

        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_foreign_key(
        "fk_withdrawals_user",
        "withdrawals",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_withdrawals_user", "withdrawals", ["user_id"])
    op.create_index("ix_withdrawals_status", "withdrawals", ["status"])


def downgrade() -> None:
    op.drop_index("ix_withdrawals_status", table_name="withdrawals")
    op.drop_index("ix_withdrawals_user", table_name="withdrawals")
    op.drop_table("withdrawals")

    op.drop_index("ix_wallet_ledger_order", table_name="wallet_ledger")
    op.drop_index("ix_wallet_ledger_type", table_name="wallet_ledger")
    op.drop_index("ix_wallet_ledger_user", table_name="wallet_ledger")
    op.drop_table("wallet_ledger")

    op.drop_table("wallets")
