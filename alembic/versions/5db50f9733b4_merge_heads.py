"""merge heads

Revision ID: 5db50f9733b4
Revises: 8c8c8c8c8c8c, hotfix_20260129160557_withdrawals_fiat_cols
Create Date: 2026-02-04 10:37:24.859749

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5db50f9733b4'
down_revision: Union[str, Sequence[str], None] = ('8c8c8c8c8c8c', 'hotfix_20260129160557_withdrawals_fiat_cols')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
