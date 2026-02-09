"""hotfix withdrawals fiat columns

Revision ID: 1f_hotfix_withdrawals_fiat
Revises: e62522510952
Create Date: 2026-01-29 16:03:00.445757

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1f_hotfix_withdrawals_fiat'
down_revision: Union[str, Sequence[str], None] = 'e62522510952'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
