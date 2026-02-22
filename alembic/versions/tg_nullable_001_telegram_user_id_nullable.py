"""telegram_user_id nullable

Revision ID: tg_nullable_001
Create Date: 2026-02-19
"""
from alembic import op
import sqlalchemy as sa

revision = "tg_nullable_001"
down_revision = None  # IMPORTANTE: ajustar al head actual de alembic
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        UPDATE users
        SET telegram_user_id = NULL, updated_at = now()
        WHERE telegram_user_id < 0
    """)

    op.alter_column(
        "users",
        "telegram_user_id",
        existing_type=sa.BigInteger(),
        nullable=True,
    )

    op.create_check_constraint(
        "chk_telegram_user_id_positive",
        "users",
        "telegram_user_id IS NULL OR telegram_user_id > 0",
    )


def downgrade() -> None:
    op.drop_constraint("chk_telegram_user_id_positive", "users", type_="check")

    op.execute("""
        UPDATE users
        SET telegram_user_id = -(id + 2000000000), updated_at = now()
        WHERE telegram_user_id IS NULL
    """)

    op.alter_column(
        "users",
        "telegram_user_id",
        existing_type=sa.BigInteger(),
        nullable=False,
    )