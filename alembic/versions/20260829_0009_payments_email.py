"""add payments columns, email_outbox, order status refund (step 8)

Revision ID: 0009_payments_email
Revises: 0008_audit_log
Create Date: 2026-08-29

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0009_payments_email"
down_revision: Union[str, None] = "0008_audit_log"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add columns to payments table
    op.add_column("payments", sa.Column("idempotency_key", sa.String(length=255), nullable=True))
    op.add_column("payments", sa.Column("method", sa.String(length=16), nullable=False, server_default="card"))
    op.add_column("payments", sa.Column("currency", sa.String(length=8), nullable=False, server_default="RUB"))
    op.add_column("payments", sa.Column("gateway", sa.String(length=32), nullable=False, server_default="mock"))
    op.add_column("payments", sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_payments_idempotency_key"), "payments", ["idempotency_key"], unique=False)

    # Create email_outbox table
    op.create_table(
        "email_outbox",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("to", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=512), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("template", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_email_outbox")),
    )
    op.create_index(op.f("ix_email_outbox_to"), "email_outbox", ["to"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_email_outbox_to"), table_name="email_outbox")
    op.drop_table("email_outbox")
    op.drop_index(op.f("ix_payments_idempotency_key"), table_name="payments")
    op.drop_column("payments", "paid_at")
    op.drop_column("payments", "gateway")
    op.drop_column("payments", "currency")
    op.drop_column("payments", "method")
    op.drop_column("payments", "idempotency_key")
