"""make orders.client_id nullable for cashier

Revision ID: 20260901_0011
Revises: 20260829_0010
Create Date: 2026-09-01
"""

from alembic import op
import sqlalchemy as sa

revision = "20260901_0011"
down_revision = "20260829_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("orders", "client_id", existing_type=sa.dialects.postgresql.UUID(), nullable=True)


def downgrade() -> None:
    op.alter_column("orders", "client_id", existing_type=sa.dialects.postgresql.UUID(), nullable=False)
