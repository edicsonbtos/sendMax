"""create_clients_table

Revision ID: f123456789ab
Revises: fb8906ff267a
Create Date: 2026-03-06 15:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f123456789ab'
down_revision: Union[str, Sequence[str], None] = 'fb8906ff267a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'clients',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('operator_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('total_orders', sa.Integer(), server_default='0'),
        sa.Column('total_volume', sa.Numeric(18, 2), server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('idx_clients_operator', 'clients', ['operator_id'])
    op.create_index('idx_clients_name', 'clients', ['operator_id', 'full_name'])
    op.create_unique_constraint('uq_client_operator_name_phone', 'clients', ['operator_id', 'full_name', 'phone'])
    
    op.add_column('orders', sa.Column('client_id', sa.Integer(), sa.ForeignKey('clients.id'), nullable=True))
    op.create_index('idx_orders_client', 'orders', ['client_id'])


def downgrade() -> None:
    op.drop_index('idx_orders_client', table_name='orders')
    op.drop_column('orders', 'client_id')
    op.drop_table('clients')
