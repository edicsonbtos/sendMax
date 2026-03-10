"""create daily_closures table

Revision ID: create_daily_closures_table
Revises: f123456789ab
Create Date: 2026-03-09

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'create_daily_closures_table'
down_revision = 'f123456789ab'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'daily_closures',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('closure_date', sa.Date(), nullable=False),
        sa.Column('total_orders_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_volume_origin', sa.Numeric(precision=20, scale=2), nullable=False, server_default='0'),
        sa.Column('total_profit_usdt', sa.Numeric(precision=20, scale=8), nullable=False, server_default='0'),
        sa.Column('total_profit_real', sa.Numeric(precision=20, scale=8), nullable=False, server_default='0'),
        sa.Column('success_rate', sa.Numeric(precision=5, scale=2), nullable=False, server_default='100'),
        
        # Rankings
        sa.Column('best_operator_id', sa.BigInteger(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('best_operator_alias', sa.String(length=100), nullable=True),
        sa.Column('best_origin_country', sa.String(length=50), nullable=True),
        sa.Column('best_dest_country', sa.String(length=50), nullable=True),
        
        # Withdrawals
        sa.Column('pending_withdrawals_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('pending_withdrawals_amount', sa.Numeric(precision=20, scale=8), nullable=False, server_default='0'),
        
        # Snapshots
        sa.Column('vaults_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('wallet_balances_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        
        # Logs & Audit
        sa.Column('warnings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('executed_by', sa.BigInteger(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('closure_date', name='uq_daily_closure_date')
    )
    op.create_index('idx_daily_closures_date', 'daily_closures', ['closure_date'])

def downgrade():
    op.drop_index('idx_daily_closures_date', table_name='daily_closures')
    op.drop_table('daily_closures')
