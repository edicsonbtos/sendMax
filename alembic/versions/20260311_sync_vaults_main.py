"""sync vaults main.py

Revision ID: sync_vaults_main
Revises: create_daily_closures_table
Create Date: 2026-03-11

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'sync_vaults_main'
down_revision = 'create_daily_closures_table'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Oficializa las columnas inyectadas previamente por main.py.
    Utilizamos sentencias SQL en bruto con IF NOT EXISTS porque 
    Neon DB ya contiene estas columnas debido a la inyección manual.
    Esto permite a Alembic avanzar su revisión sin arrojar error de 
    "column already exists".
    """
    op.execute("ALTER TABLE vaults ADD COLUMN IF NOT EXISTS type VARCHAR(50);")
    op.execute("ALTER TABLE vaults ADD COLUMN IF NOT EXISTS tipo VARCHAR(50);")


def downgrade() -> None:
    """
    Reversión de las columnas.
    """
    op.drop_column('vaults', 'tipo')
    op.drop_column('vaults', 'type')
