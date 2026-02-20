"""fix settings.updated_by type from bigint to text

La migracion original (create_settings_table_20260210) definio
updated_by como String(255). En algun momento la columna fue
cambiada a bigint en la DB, causando error al insertar strings
como 'user:8' o 'migration'.

Este fix restaura el tipo correcto.

Revision ID: fix_settings_updated_by_type
Revises: a1b2c3_add_login_fields
Create Date: 2026-02-20
"""
from alembic import op
import sqlalchemy as sa

revision = 'fix_settings_updated_by_type'
down_revision = 'a1b2c3_add_login_fields'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        'settings',
        'updated_by',
        existing_type=sa.BigInteger(),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade():
    # Primero limpiar valores no numericos
    op.execute("UPDATE settings SET updated_by = NULL WHERE updated_by !~ '^[0-9]+$'")
    op.alter_column(
        'settings',
        'updated_by',
        existing_type=sa.Text(),
        type_=sa.BigInteger(),
        existing_nullable=True,
        postgresql_using='updated_by::bigint',
    )