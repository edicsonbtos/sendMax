"""add origin receipts table

Revision ID: 4da93e6227ac
Revises: 5db50f9733b4
Create Date: 2026-02-04 10:38:46.986003

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4da93e6227ac'
down_revision: Union[str, Sequence[str], None] = '5db50f9733b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "origin_receipts_daily",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("day", sa.Date(), nullable=False),  # día de negocio (UTC o tu TZ; se define en reporting)
        sa.Column("origin_country", sa.Text(), nullable=False),  # usar el mismo code que orders.origin_country
        sa.Column("fiat_currency", sa.Text(), nullable=False),  # ej: CLP, PEN (si aplica distinto al country)
        sa.Column("amount_fiat", sa.Numeric(18, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by_telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),

        # Cierre / verificación (backoffice o Telegram)
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("approved_note", sa.Text(), nullable=True),

        # Para enlazar opcionalmente a una orden específica (si luego lo necesitas)
        sa.Column("ref_order_public_id", sa.BigInteger(), nullable=True),
    )

    op.create_index(
        "ix_origin_receipts_daily_day_country",
        "origin_receipts_daily",
        ["day", "origin_country"],
        unique=False,
    )

    op.create_index(
        "ux_origin_receipts_daily_day_country_currency",
        "origin_receipts_daily",
        ["day", "origin_country", "fiat_currency"],
        unique=True,
    )



def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ux_origin_receipts_daily_day_country_currency", table_name="origin_receipts_daily")
    op.drop_index("ix_origin_receipts_daily_day_country", table_name="origin_receipts_daily")
    op.drop_table("origin_receipts_daily")

