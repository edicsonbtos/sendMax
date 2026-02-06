"""create origin_wallet_closures table

Revision ID: 1c2d3e_origin_wallet_closures
Revises: 97fa8cee3e0c
Create Date: 2026-02-06
"""
from alembic import op
import sqlalchemy as sa

revision = "1c2d3e_origin_wallet_closures"
down_revision = "97fa8cee3e0c"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "origin_wallet_closures",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("origin_country", sa.Text(), nullable=False),
        sa.Column("fiat_currency", sa.Text(), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("closed_by_telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("net_amount_at_close", sa.Numeric(), nullable=False),
    )
    op.create_unique_constraint(
        "uq_origin_wallet_closures_day_country_curr",
        "origin_wallet_closures",
        ["day", "origin_country", "fiat_currency"],
    )
    op.create_index("ix_origin_wallet_closures_day", "origin_wallet_closures", ["day"])

def downgrade() -> None:
    op.drop_index("ix_origin_wallet_closures_day", table_name="origin_wallet_closures")
    op.drop_constraint("uq_origin_wallet_closures_day_country_curr", "origin_wallet_closures", type_="unique")
    op.drop_table("origin_wallet_closures")
