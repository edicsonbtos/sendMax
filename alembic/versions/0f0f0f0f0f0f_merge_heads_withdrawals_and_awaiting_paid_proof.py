"""merge heads: withdrawals_fiat_cols + awaiting_paid_proof

Revision ID: 0f0f0f0f0f0f
Revises: 1f2_withdrawals_fiat_cols, 9a1b2c3d4e5f
Create Date: 2026-02-02
"""
from typing import Sequence, Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0f0f0f0f0f0f"
down_revision: Union[str, Sequence[str], None] = ("1f2_withdrawals_fiat_cols", "9a1b2c3d4e5f")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # merge only
    pass

def downgrade() -> None:
    # merge only
    pass
