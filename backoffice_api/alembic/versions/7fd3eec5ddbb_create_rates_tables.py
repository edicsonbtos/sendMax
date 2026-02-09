"""create rates tables

Revision ID: 7fd3eec5ddbb
Revises: b71a73ee4d14
Create Date: 2026-01-27 14:06:03.088392
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7fd3eec5ddbb"
down_revision = "b71a73ee4d14"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Versiones efectivas de tasas (9am y recalculos por 3%)
    op.create_table(
        "rate_versions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),

        # 9am / intraday
        sa.Column("kind", sa.Text(), nullable=False),  # 'daily_9am' | 'intraday_recalc'
        sa.Column("reason", sa.Text(), nullable=True),  # texto libre: "BUY Chile +3.2%" etc.

        # Vigencia
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),

        # Estado
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )

    # Precios BUY/SELL por país usados para construir ESA versión
    op.create_table(
        "p2p_country_prices",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("rate_version_id", sa.BigInteger(), nullable=False),

        sa.Column("country", sa.Text(), nullable=False),  # 'USA','CHILE','PERU',...
        sa.Column("fiat", sa.Text(), nullable=False),     # 'USD','CLP',...
        sa.Column("buy_price", sa.Numeric(18, 8), nullable=False),   # fiat por 1 USDT
        sa.Column("sell_price", sa.Numeric(18, 8), nullable=False),  # fiat por 1 USDT

        # Metadata de consulta (trazabilidad)
        sa.Column("methods_used", sa.Text(), nullable=True),       # "Zelle" o "BancoEstado,Santander"
        sa.Column("amount_ref", sa.Numeric(18, 2), nullable=True), # transAmount usado
        sa.Column("source", sa.Text(), nullable=False, server_default="binance_p2p"),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_foreign_key(
        "fk_p2p_prices_version",
        "p2p_country_prices",
        "rate_versions",
        ["rate_version_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_p2p_prices_version", "p2p_country_prices", ["rate_version_id"])
    op.create_index("ix_p2p_prices_country", "p2p_country_prices", ["country"])

    # Tasas por ruta dentro de una versión
    op.create_table(
        "route_rates",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("rate_version_id", sa.BigInteger(), nullable=False),

        sa.Column("origin_country", sa.Text(), nullable=False),
        sa.Column("dest_country", sa.Text(), nullable=False),

        sa.Column("commission_pct", sa.Numeric(5, 2), nullable=False),  # 6.00 / 10.00
        sa.Column("buy_origin", sa.Numeric(18, 8), nullable=False),
        sa.Column("sell_dest", sa.Numeric(18, 8), nullable=False),

        sa.Column("rate_base", sa.Numeric(18, 10), nullable=False),
        sa.Column("rate_client", sa.Numeric(18, 10), nullable=False),

        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_foreign_key(
        "fk_route_rates_version",
        "route_rates",
        "rate_versions",
        ["rate_version_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_route_rates_version", "route_rates", ["rate_version_id"])
    op.create_index("ix_route_rates_route", "route_rates", ["origin_country", "dest_country"])


def downgrade() -> None:
    op.drop_index("ix_route_rates_route", table_name="route_rates")
    op.drop_index("ix_route_rates_version", table_name="route_rates")
    op.drop_table("route_rates")

    op.drop_index("ix_p2p_prices_country", table_name="p2p_country_prices")
    op.drop_index("ix_p2p_prices_version", table_name="p2p_country_prices")
    op.drop_table("p2p_country_prices")

    op.drop_table("rate_versions")