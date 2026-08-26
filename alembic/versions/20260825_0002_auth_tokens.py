"""add refresh_tokens and client lockout fields

Revision ID: 0002_auth_tokens
Revises: 0001_auth_slice
Create Date: 2026-08-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_auth_tokens"
down_revision: Union[str, None] = "0001_auth_slice"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_type", sa.String(length=16), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("jti", sa.Uuid(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("jti", name="uq_refresh_tokens_jti"),
    )
    op.create_index("ix_refresh_tokens_user_type", "refresh_tokens", ["user_type"])
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.add_column(
        "clients",
        sa.Column("failed_attempts", sa.Integer(), nullable=True),
    )
    op.add_column(
        "clients",
        sa.Column("locked_until", sa.DateTime(timezone=True)),
    )
    op.execute("UPDATE clients SET failed_attempts = 0 WHERE failed_attempts IS NULL")
    op.alter_column("clients", "failed_attempts", nullable=False, server_default="0")


def downgrade() -> None:
    op.drop_column("clients", "locked_until")
    op.drop_column("clients", "failed_attempts")
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_user_type", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
