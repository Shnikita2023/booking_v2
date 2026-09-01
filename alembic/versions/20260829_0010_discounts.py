"""add discounts table for global and per-client discounts

Revision ID: 0010_discounts
Revises: 0009_payments_email
Create Date: 2026-08-29

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0010_discounts"
down_revision: Union[str, None] = "0009_payments_email"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "discounts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("percent", sa.Integer(), nullable=False),
        sa.Column("discount_type", sa.String(length=16), nullable=False, server_default="global"),
        sa.Column("event_id", sa.Uuid(), sa.ForeignKey("events.id"), nullable=True),
        sa.Column("client_id", sa.Uuid(), sa.ForeignKey("clients.id"), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_discounts_event_id", "discounts", ["event_id"])
    op.create_index("ix_discounts_client_id", "discounts", ["client_id"])


def downgrade() -> None:
    op.drop_table("discounts")
