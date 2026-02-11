"""merge heads: origin verification + origin sweeps

Revision ID: 97fa8cee3e0c
Revises: 322998ee4a41, 9f1b8c_origin_sweeps
Create Date: 2026-02-06 10:31:37.810231

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '97fa8cee3e0c'
down_revision: Union[str, Sequence[str], None] = ('322998ee4a41', '9f1b8c_origin_sweeps')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
