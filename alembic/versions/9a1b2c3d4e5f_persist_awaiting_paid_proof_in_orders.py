"""persist awaiting paid proof state in orders

Revision ID: 9a1b2c3d4e5f
Revises: 3c3f537e3f23
Create Date: 2026-02-02
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "9a1b2c3d4e5f"
down_revision: Union[str, Sequence[str], None] = "e62522510952"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("awaiting_paid_proof", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "orders",
        sa.Column("awaiting_paid_proof_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("awaiting_paid_proof_by", sa.BigInteger(), nullable=True),
    )
    op.create_index("ix_orders_awaiting_paid_proof", "orders", ["awaiting_paid_proof"])


def downgrade() -> None:
    op.drop_index("ix_orders_awaiting_paid_proof", table_name="orders")
    op.drop_column("orders", "awaiting_paid_proof_by")
    op.drop_column("orders", "awaiting_paid_proof_at")
    op.drop_column("orders", "awaiting_paid_proof")



