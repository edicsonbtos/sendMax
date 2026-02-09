"""add profit_usdt to orders

Revision ID: 3c3f537e3f23
Revises: 47c816e9a216
Create Date: 2026-01-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3c3f537e3f23"
down_revision: Union[str, Sequence[str], None] = "47c816e9a216"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("profit_usdt", sa.Numeric(18, 8), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "profit_usdt")
