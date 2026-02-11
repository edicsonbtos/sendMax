"""merge settings and origin_wallet_closures

Revision ID: 30bb5fcf3040
Revises: 1c2d3e_origin_wallet_closures, create_settings_table_20260210
Create Date: 2026-02-10 22:52:54.364020

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '30bb5fcf3040'
down_revision: Union[str, Sequence[str], None] = ('1c2d3e_origin_wallet_closures', 'create_settings_table_20260210')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
