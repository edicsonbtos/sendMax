"""add partial unique index to wallet_ledger for idempotency

Revision ID: e3d5663dda88
Revises: fb8906ff267a
Create Date: 2026-02-22 21:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3d5663dda88'
down_revision: Union[str, Sequence[str], None] = 'fb8906ff267a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ux_wallet_ledger_idempotency",
        "wallet_ledger",
        ["user_id", "type", "ref_order_public_id"],
        unique=True,
        postgresql_where=sa.text("ref_order_public_id IS NOT NULL")
    )


def downgrade() -> None:
    op.drop_index("ux_wallet_ledger_idempotency", table_name="wallet_ledger")
