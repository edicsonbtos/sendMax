"""create orders public_id sequence

Revision ID: 2c20eda69bd2
Revises: 8249dc838371
Create Date: 2026-01-28
"""

from typing import Sequence, Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2c20eda69bd2"
down_revision: Union[str, Sequence[str], None] = "8249dc838371"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Sequence global para public_id (numérico, atómico)
    op.execute("CREATE SEQUENCE IF NOT EXISTS orders_public_id_seq;")

    # Si ya hay órdenes, arrancar desde max(public_id)+1.
    # `is_called=false` hace que el próximo nextval() devuelva exactamente ese valor.
    op.execute(
        """
        SELECT setval(
            'orders_public_id_seq',
            COALESCE((SELECT MAX(public_id) FROM orders), 0) + 1,
            false
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP SEQUENCE IF EXISTS orders_public_id_seq;")