"""extend withdrawals for fiat payouts

Revision ID: e62522510952
Revises: 3c3f537e3f23
Create Date: 2026-01-29 15:33:56.005719

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e62522510952'
down_revision: Union[str, Sequence[str], None] = '3c3f537e3f23'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
