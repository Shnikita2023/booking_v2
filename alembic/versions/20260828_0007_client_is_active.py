"""add is_active column to clients for admin block/unblock

Revision ID: 0007_client_is_active
Revises: 0006_settings
Create Date: 2026-08-28

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0007_client_is_active"
down_revision: Union[str, None] = "0006_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("clients", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade() -> None:
    op.drop_column("clients", "is_active")
