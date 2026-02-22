"""add dest payment proof to orders

Revision ID: 4876012249fd
Revises: 2c20eda69bd2
Create Date: 2026-01-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4876012249fd"
down_revision: Union[str, Sequence[str], None] = "2c20eda69bd2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Comprobante de pago en DESTINO (foto) + timestamp de pago
    op.add_column("orders", sa.Column("dest_payment_proof_file_id", sa.Text(), nullable=True))
    op.add_column("orders", sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "paid_at")
    op.drop_column("orders", "dest_payment_proof_file_id")
