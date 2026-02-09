"""create origin_sweeps table (origin wallet outflows)

Revision ID: 9f1b8c_origin_sweeps
Revises: 4da93e6227ac
Create Date: 2026-02-06
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "9f1b8c_origin_sweeps"
down_revision = "4da93e6227ac"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "origin_sweeps",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("origin_country", sa.Text(), nullable=False),
        sa.Column("fiat_currency", sa.Text(), nullable=False),
        sa.Column("amount_fiat", sa.Numeric(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("external_ref", sa.Text(), nullable=True),  # id de retiro/binance o referencia manual
    )
    op.create_index("ix_origin_sweeps_day", "origin_sweeps", ["day"])
    op.create_index("ix_origin_sweeps_origin_country", "origin_sweeps", ["origin_country"])
    op.create_index(
        "uq_origin_sweeps_day_country_curr_ref",
        "origin_sweeps",
        ["day", "origin_country", "fiat_currency", "external_ref"],
        unique=True,
    )

def downgrade() -> None:
    op.drop_index("uq_origin_sweeps_day_country_curr_ref", table_name="origin_sweeps")
    op.drop_index("ix_origin_sweeps_origin_country", table_name="origin_sweeps")
    op.drop_index("ix_origin_sweeps_day", table_name="origin_sweeps")
    op.drop_table("origin_sweeps")
