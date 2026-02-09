"""add cancel reason to orders

Revision ID: c525e594bdd5
Revises: 4876012249fd
Create Date: 2026-01-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c525e594bdd5"
down_revision: Union[str, Sequence[str], None] = "4876012249fd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("cancel_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "cancel_reason")
