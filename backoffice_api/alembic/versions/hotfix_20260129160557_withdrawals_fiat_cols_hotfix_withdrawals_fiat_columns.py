"""hotfix withdrawals fiat columns

Revision ID: hotfix_20260129160557_withdrawals_fiat_cols
Revises: e62522510952
Create Date: 2026-01-29 16:05:58.951785
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "hotfix_20260129160557_withdrawals_fiat_cols"
down_revision = "e62522510952"
branch_labels = None
depends_on = None


def _has_column(conn, table_name: str, column_name: str) -> bool:
    row = conn.execute(sa.text("""
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema='public'
          AND table_name=:t
          AND column_name=:c
        LIMIT 1
    """), {"t": table_name, "c": column_name}).fetchone()
    return row is not None


def upgrade() -> None:
    conn = op.get_bind()

    if not _has_column(conn, "withdrawals", "country"):
        op.add_column("withdrawals", sa.Column("country", sa.Text(), nullable=True))

    if not _has_column(conn, "withdrawals", "fiat"):
        op.add_column("withdrawals", sa.Column("fiat", sa.Text(), nullable=True))

    if not _has_column(conn, "withdrawals", "fiat_amount"):
        op.add_column("withdrawals", sa.Column("fiat_amount", sa.Numeric(18, 2), nullable=True))

    if not _has_column(conn, "withdrawals", "reject_reason"):
        op.add_column("withdrawals", sa.Column("reject_reason", sa.Text(), nullable=True))

    if not _has_column(conn, "withdrawals", "resolved_at"):
        op.add_column("withdrawals", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # best-effort
    conn = op.get_bind()

    if _has_column(conn, "withdrawals", "resolved_at"):
        op.drop_column("withdrawals", "resolved_at")
    if _has_column(conn, "withdrawals", "reject_reason"):
        op.drop_column("withdrawals", "reject_reason")
    if _has_column(conn, "withdrawals", "fiat_amount"):
        op.drop_column("withdrawals", "fiat_amount")
    if _has_column(conn, "withdrawals", "fiat"):
        op.drop_column("withdrawals", "fiat")
    if _has_column(conn, "withdrawals", "country"):
        op.drop_column("withdrawals", "country")
