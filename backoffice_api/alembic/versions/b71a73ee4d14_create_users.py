"""create users

Revision ID: b71a73ee4d14
Revises:
Create Date: 2026-01-27
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b71a73ee4d14"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) Habilita citext para alias case-insensitive (si no existe)
    op.execute("CREATE EXTENSION IF NOT EXISTS citext;")

    # 2) Tabla users
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("alias", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False, server_default="operator"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        # Referidos: padrino_id -> users.id (nullable)
        sa.Column("sponsor_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # 3) Convertimos alias a CITEXT y lo hacemos único (case-insensitive)
    op.execute("ALTER TABLE users ALTER COLUMN alias TYPE CITEXT;")
    op.create_unique_constraint("uq_users_alias", "users", ["alias"])

    # 4) FK sponsor_id -> users.id
    op.create_foreign_key(
        "fk_users_sponsor",
        "users",
        "users",
        ["sponsor_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_users_sponsor", "users", type_="foreignkey")
    op.drop_constraint("uq_users_alias", "users", type_="unique")
    op.drop_table("users")

    # No borramos la extensión citext en downgrade para no afectar otras tablas.