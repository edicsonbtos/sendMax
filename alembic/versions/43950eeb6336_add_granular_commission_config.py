"""add granular commission config

Revision ID: 43950eeb6336
Revises: 682f8674ab42
Create Date: 2026-02-23
"""

from alembic import op

revision = '43950eeb6336'
down_revision = '682f8674ab42'

def upgrade() -> None:
    # Insertar configs iniciales (idempotent)
    op.execute("""
        INSERT INTO settings (key, value_json, updated_at, updated_by)
        VALUES
            ('commission_routes', '{}', NOW(), 'migration:granular_config'),
            ('profit_split', '{"operator_with_sponsor": 0.45, "sponsor": 0.10, "operator_solo": 0.50}', NOW(), 'migration:granular_config')
        ON CONFLICT (key) DO NOTHING;
    """)

    # Normalizar configs existentes a formato decimal si detecta enteros (ej: 6 -> 0.06)
    # value_json es tipo JSON, casteamos a JSONB para operar y volvemos a JSON.
    op.execute("""
        UPDATE settings
        SET value_json = (
            jsonb_set(
                value_json::jsonb,
                '{percent}',
                to_jsonb(((value_json->>'percent')::float / 100))
            )
        )::json,
            updated_at = NOW(),
            updated_by = 'migration:decimal_normalization'
        WHERE key IN ('margin_default', 'margin_dest_venez', 'margin_route_usa_venez')
          AND (value_json->>'percent') IS NOT NULL
          AND (value_json->>'percent')::float >= 1.0;
    """)

def downgrade() -> None:
    op.execute("DELETE FROM settings WHERE key IN ('commission_routes', 'profit_split');")
