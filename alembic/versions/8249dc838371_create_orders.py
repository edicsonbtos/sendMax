"""create orders

Revision ID: 8249dc838371
Revises: 1b0d81fcbce5
Create Date: 2026-01-27 22:36:19.485536
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8249dc838371"
down_revision: Union[str, Sequence[str], None] = "1b0d81fcbce5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Orders (MVP)

    - Estado inicial: CREADA
    - Snapshot de tasas al crear:
      rate_version_id, commission_pct, rate_client, payout_dest
    - Comprobante obligatorio: guardamos telegram_file_id por ahora
      (luego se reemplaza/expande a Cloudinary URL)
    """

    op.create_table(
        "orders",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),

        # Consecutivo visible (lo generaremos en app)
        sa.Column("public_id", sa.BigInteger(), nullable=False, unique=True),

        # Operador (usuario Telegram registrado)
        sa.Column("operator_user_id", sa.BigInteger(), nullable=False),

        # Ruta
        sa.Column("origin_country", sa.Text(), nullable=False),
        sa.Column("dest_country", sa.Text(), nullable=False),

        # Monto origen (fiat)
        sa.Column("amount_origin", sa.Numeric(18, 2), nullable=False),

        # Snapshot de tasa
        sa.Column("rate_version_id", sa.BigInteger(), nullable=False),
        sa.Column("commission_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("rate_client", sa.Numeric(18, 10), nullable=False),

        # Resultado (pago destino calculado)
        sa.Column("payout_dest", sa.Numeric(18, 2), nullable=False),

        # Datos beneficiario (texto copiado/pegado)
        sa.Column("beneficiary_text", sa.Text(), nullable=False),

        # Comprobante (obligatorio). Por ahora: file_id de Telegram
        sa.Column("origin_payment_proof_file_id", sa.Text(), nullable=False),

        # Estado
        sa.Column("status", sa.Text(), nullable=False, server_default="CREADA"),

        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # FK: orders.operator_user_id -> users.id
    op.create_foreign_key(
        "fk_orders_operator_user",
        "orders",
        "users",
        ["operator_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # FK: orders.rate_version_id -> rate_versions.id
    op.create_foreign_key(
        "fk_orders_rate_version",
        "orders",
        "rate_versions",
        ["rate_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_index("ix_orders_status", "orders", ["status"])
    op.create_index("ix_orders_created_at", "orders", ["created_at"])
    op.create_index("ix_orders_operator_user_id", "orders", ["operator_user_id"])


def downgrade() -> None:
    op.drop_index("ix_orders_operator_user_id", table_name="orders")
    op.drop_index("ix_orders_created_at", table_name="orders")
    op.drop_index("ix_orders_status", table_name="orders")

    op.drop_constraint("fk_orders_rate_version", "orders", type_="foreignkey")
    op.drop_constraint("fk_orders_operator_user", "orders", type_="foreignkey")

    op.drop_table("orders")