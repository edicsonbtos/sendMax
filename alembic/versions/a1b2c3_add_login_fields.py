"""add email and hashed_password to users for backoffice login

Revision ID: a1b2c3_add_login_fields
Revises: add_execution_prices_20260211
Create Date: 2026-02-15
"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3_add_login_fields'
down_revision = 'add_execution_prices_20260211'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('users')]

    if 'email' not in columns:
        op.add_column('users', sa.Column('email', sa.Text(), nullable=True))
        op.create_unique_constraint('uq_users_email', 'users', ['email'])

    if 'hashed_password' not in columns:
        op.add_column('users', sa.Column('hashed_password', sa.Text(), nullable=True))


def downgrade():
    op.drop_constraint('uq_users_email', 'users', type_='unique')
    op.drop_column('users', 'hashed_password')
    op.drop_column('users', 'email')
