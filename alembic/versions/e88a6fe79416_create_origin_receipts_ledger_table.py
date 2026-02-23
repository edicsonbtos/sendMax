"""create origin_receipts_ledger table

Revision ID: e88a6fe79416
Revises: e3d5663dda88
Create Date: 2026-02-22 21:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e88a6fe79416'
down_revision: Union[str, Sequence[str], None] = 'e3d5663dda88'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "origin_receipts_ledger",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("ref_order_public_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("origin_country", sa.Text(), nullable=False),
        sa.Column("fiat_currency", sa.Text(), nullable=False),
        sa.Column("amount_fiat", sa.Numeric(18, 2), nullable=False),
        sa.Column("approved_by_telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("approved_note", sa.Text(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_origin_receipts_ledger_order", "origin_receipts_ledger", ["ref_order_public_id"])


def downgrade() -> None:
    op.drop_table("origin_receipts_ledger")
