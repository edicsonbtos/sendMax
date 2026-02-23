"""add check constraint to wallets for non-negative balance

Revision ID: 1f1b48bdb3b8
Revises: e88a6fe79416
Create Date: 2026-02-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1f1b48bdb3b8'
down_revision: Union[str, Sequence[str], None] = 'e88a6fe79416'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_check_constraint(
        "chk_wallets_balance_non_negative",
        "wallets",
        "balance_usdt >= 0"
    )


def downgrade() -> None:
    op.drop_constraint("chk_wallets_balance_non_negative", "wallets", type_="check")
