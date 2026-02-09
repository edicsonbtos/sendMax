"""create user_contacts table for broadcast/post-reset

Revision ID: 8c8c8c8c8c8c
Revises: 6aa111bb22cc
Create Date: 2026-02-02
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "8c8c8c8c8c8c"
down_revision: Union[str, Sequence[str], None] = "6aa111bb22cc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_contacts",
        sa.Column("telegram_user_id", sa.BigInteger(), primary_key=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_user_contacts_last_seen_at", "user_contacts", ["last_seen_at"])


def downgrade() -> None:
    op.drop_index("ix_user_contacts_last_seen_at", table_name="user_contacts")
    op.drop_table("user_contacts")
