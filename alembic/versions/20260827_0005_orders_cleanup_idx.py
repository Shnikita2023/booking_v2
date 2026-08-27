"""add index on orders(status, reserved_until) for cleanup scan

Revision ID: 0005_orders_cleanup_idx
Revises: 0004_orders
Create Date: 2026-08-27

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0005_orders_cleanup_idx"
down_revision: Union[str, None] = "0004_orders"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_orders_status_reserved_until",
        "orders",
        ["status", "reserved_until"],
    )


def downgrade() -> None:
    op.drop_index("ix_orders_status_reserved_until", table_name="orders")
