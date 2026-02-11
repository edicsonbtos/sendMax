"""add execution prices and profit real

Revision ID: add_execution_prices_20260211
Revises: 30bb5fcf3040
Create Date: 2026-02-11 02:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'add_execution_prices_20260211'
down_revision = '30bb5fcf3040'
branch_labels = None
depends_on = None


def upgrade():
    # Verificar si las columnas ya existen (idempotente)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('orders')]
    
    if 'execution_price_buy' not in columns:
        op.add_column('orders', sa.Column('execution_price_buy', sa.Numeric(18, 8), nullable=True))
    
    if 'execution_price_sell' not in columns:
        op.add_column('orders', sa.Column('execution_price_sell', sa.Numeric(18, 8), nullable=True))
    
    # profit_real_usdt ya existe según tu verificación, pero lo dejamos por si acaso
    if 'profit_real_usdt' not in columns:
        op.add_column('orders', sa.Column('profit_real_usdt', sa.Numeric(18, 8), nullable=True))


def downgrade():
    op.drop_column('orders', 'execution_price_sell')
    op.drop_column('orders', 'execution_price_buy')
    # No borramos profit_real_usdt porque existía antes
