"""add origin verification audit fields to orders

Revision ID: 322998ee4a41
Revises: 4da93e6227ac
Create Date: 2026-02-04 12:15:40.438350

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '322998ee4a41'
down_revision: Union[str, Sequence[str], None] = '4da93e6227ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("orders", sa.Column("origin_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("orders", sa.Column("origin_verified_by_telegram_id", sa.BigInteger(), nullable=True))
    op.add_column("orders", sa.Column("origin_verified_by_name", sa.Text(), nullable=True))

    op.create_index("ix_orders_origin_verified_at", "orders", ["origin_verified_at"], unique=False)



def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_orders_origin_verified_at", table_name="orders")
    op.drop_column("orders", "origin_verified_by_name")
    op.drop_column("orders", "origin_verified_by_telegram_id")
    op.drop_column("orders", "origin_verified_at")

