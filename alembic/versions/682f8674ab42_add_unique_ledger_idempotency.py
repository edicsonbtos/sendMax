"""add unique ledger idempotency

Revision ID: 682f8674ab42
Revises: 1f1b48bdb3b8
Create Date: 2026-02-23 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '682f8674ab42'
down_revision: Union[str, Sequence[str], None] = '1f1b48bdb3b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Dropping old index name if it exists from previous iterations
    op.execute("DROP INDEX IF EXISTS ux_wallet_ledger_idempotency")

    op.create_index(
        'idx_ledger_idempotency',
        'wallet_ledger',
        ['user_id', 'type', 'ref_order_public_id'],
        unique=True,
        postgresql_where=sa.text('ref_order_public_id IS NOT NULL')
    )


def downgrade() -> None:
    op.drop_index('idx_ledger_idempotency', table_name='wallet_ledger')
