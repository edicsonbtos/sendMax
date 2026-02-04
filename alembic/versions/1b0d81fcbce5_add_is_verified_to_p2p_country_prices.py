"""add is_verified to p2p_country_prices

Revision ID: 1b0d81fcbce5
Revises: 7fd3eec5ddbb
Create Date: 2026-01-27 18:17:08.238572
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1b0d81fcbce5"
down_revision: Union[str, Sequence[str], None] = "7fd3eec5ddbb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Guardamos si el anuncio fue verificado o si fue fallback (no verificado)
    op.add_column(
        "p2p_country_prices",
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )


def downgrade() -> None:
    op.drop_column("p2p_country_prices", "is_verified")