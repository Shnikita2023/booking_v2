"""create audit_log table for the append-only action journal (D-2, D-3, S-7)

Revision ID: 0008_audit_log
Revises: 0007_client_is_active
Create Date: 2026-08-28

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0008_audit_log"
down_revision: Union[str, None] = "0007_client_is_active"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_type", sa.String(length=16), nullable=True),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("actor_role", sa.String(length=32), nullable=True),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=True),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_log")),
    )
    op.create_index(op.f("ix_audit_log_actor_type"), "audit_log", ["actor_type"], unique=False)
    op.create_index(op.f("ix_audit_log_actor_id"), "audit_log", ["actor_id"], unique=False)
    op.create_index(op.f("ix_audit_log_action"), "audit_log", ["action"], unique=False)
    op.create_index(op.f("ix_audit_log_created_at"), "audit_log", ["created_at"], unique=False)
    op.create_index(op.f("ix_audit_log_entity_type"), "audit_log", ["entity_type"], unique=False)
    op.create_index(
        op.f("ix_audit_entity"), "audit_log", ["entity_type", "entity_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_entity"), table_name="audit_log")
    op.drop_index(op.f("ix_audit_log_entity_type"), table_name="audit_log")
    op.drop_index(op.f("ix_audit_log_created_at"), table_name="audit_log")
    op.drop_index(op.f("ix_audit_log_action"), table_name="audit_log")
    op.drop_index(op.f("ix_audit_log_actor_id"), table_name="audit_log")
    op.drop_index(op.f("ix_audit_log_actor_type"), table_name="audit_log")
    op.drop_table("audit_log")
