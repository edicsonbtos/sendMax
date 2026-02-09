"""add kyc fields and payout method to users

Revision ID: 6aa111bb22cc
Revises: 0f0f0f0f0f0f
Create Date: 2026-02-02
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "6aa111bb22cc"
down_revision: Union[str, Sequence[str], None] = "0f0f0f0f0f0f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Datos básicos
    op.add_column("users", sa.Column("full_name", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("phone", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("address_short", sa.Text(), nullable=True))

    # Método único para cobrar ganancias (retiros)
    op.add_column("users", sa.Column("payout_country", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("payout_method_text", sa.Text(), nullable=True))

    # KYC (guardamos SOLO file_id de Telegram)
    op.add_column("users", sa.Column("kyc_doc_file_id", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("kyc_selfie_file_id", sa.Text(), nullable=True))

    # Estado KYC
    op.add_column("users", sa.Column("kyc_status", sa.Text(), nullable=False, server_default="PENDING"))
    op.add_column("users", sa.Column("kyc_submitted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("kyc_reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("kyc_review_reason", sa.Text(), nullable=True))

    op.create_index("ix_users_kyc_status", "users", ["kyc_status"])
    op.create_index("ix_users_payout_country", "users", ["payout_country"])


def downgrade() -> None:
    op.drop_index("ix_users_payout_country", table_name="users")
    op.drop_index("ix_users_kyc_status", table_name="users")

    op.drop_column("users", "kyc_review_reason")
    op.drop_column("users", "kyc_reviewed_at")
    op.drop_column("users", "kyc_submitted_at")
    op.drop_column("users", "kyc_status")

    op.drop_column("users", "kyc_selfie_file_id")
    op.drop_column("users", "kyc_doc_file_id")

    op.drop_column("users", "payout_method_text")
    op.drop_column("users", "payout_country")

    op.drop_column("users", "address_short")
    op.drop_column("users", "phone")
    op.drop_column("users", "full_name")
