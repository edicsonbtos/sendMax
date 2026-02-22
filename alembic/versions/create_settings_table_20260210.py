"""create settings table

Revision ID: create_settings_table_20260210
Revises: hotfix_20260129160557_withdrawals_fiat_cols
Create Date: 2026-02-10 22:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import String, Text, DateTime, JSON
from sqlalchemy.dialects import postgresql
import json

# revision identifiers, used by Alembic.
revision = 'create_settings_table_20260210'
down_revision = 'hotfix_20260129160557_withdrawals_fiat_cols'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Crear la tabla con value_json JSONB
    op.create_table(
        'settings',
        sa.Column('key', sa.String(length=255), nullable=False),
        sa.Column('value_json', postgresql.JSONB(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_by', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('key')
    )

    # 2. Insertar datos semilla
    settings_table = table(
        'settings',
        column('key', String),
        column('value_json', postgresql.JSONB),
        column('updated_by', String)
    )

    op.bulk_insert(
        settings_table,
        [
            {
                'key': 'p2p_rows', 
                'value_json': json.dumps({'rows': 10}),
                'updated_by': 'migration'
            },
            {
                'key': 'margin_default', 
                'value_json': json.dumps({'percent': 10.0}),
                'updated_by': 'migration'
            },
            {
                'key': 'margin_dest_venez', 
                'value_json': json.dumps({'percent': 6.0}),
                'updated_by': 'migration'
            },
            {
                'key': 'margin_route_usa_venez', 
                'value_json': json.dumps({'percent': 10.0}),
                'updated_by': 'migration'
            }
        ]
    )

def downgrade():
    op.drop_table('settings')
