"""add events, ticket_types, info_pages

Revision ID: 0003_catalog
Revises: 0002_auth_tokens
Create Date: 2026-08-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_catalog"
down_revision: Union[str, None] = "0002_auth_tokens"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_min", sa.Integer()),
        sa.Column("age_rating", sa.String(length=32)),
        sa.Column("venue", sa.String(length=255)),
        sa.Column("price", sa.Numeric(12, 2)),
        sa.Column(
            "status",
            sa.Enum(
                "draft", "on_sale", "paused", "cancelled", "moved", "completed",
                name="eventstatus", native_enum=False, length=16,
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("banner_small_url", sa.String(length=512)),
        sa.Column("banner_large_url", sa.String(length=512)),
        sa.Column(
            "show_free_tickets", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("sale_paused", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("cloned_from_id", sa.Uuid(), sa.ForeignKey("events.id")),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_events_status_starts_at", "events", ["status", "starts_at"])
    op.create_table(
        "ticket_types",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("event_id", sa.Uuid(), sa.ForeignKey("events.id"), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("quota", sa.Integer(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("price >= 0", name="ck_ticket_types_price_non_negative"),
        sa.CheckConstraint("quota >= 0", name="ck_ticket_types_quota_non_negative"),
    )
    op.create_index("ix_ticket_types_event_id", "ticket_types", ["event_id"])
    op.create_table(
        "info_pages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("updated_by", sa.Uuid()),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("slug", name="uq_info_pages_slug"),
    )


def downgrade() -> None:
    op.drop_table("info_pages")
    op.drop_index("ix_ticket_types_event_id", table_name="ticket_types")
    op.drop_table("ticket_types")
    op.drop_index("ix_events_status_starts_at", table_name="events")
    op.drop_table("events")
