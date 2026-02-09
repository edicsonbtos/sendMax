"""hotfix withdrawals fiat columns v2

Revision ID: 1f2_withdrawals_fiat_cols
Revises: 1f_hotfix_withdrawals_fiat
Create Date: 2026-01-29 16:04:15.803856

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1f2_withdrawals_fiat_cols'
down_revision: Union[str, Sequence[str], None] = '1f_hotfix_withdrawals_fiat'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
