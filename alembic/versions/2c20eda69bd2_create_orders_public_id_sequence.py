"""create orders public_id sequence

Revision ID: 2c20eda69bd2
Revises: 8249dc838371
Create Date: 2026-01-28 12:53:22.393588

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2c20eda69bd2'
down_revision: Union[str, Sequence[str], None] = '8249dc838371'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
