import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from booking.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPkMixin


def enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    return [member.value for member in enum_cls]


class EventStatus(enum.StrEnum):
    DRAFT = "draft"
    ON_SALE = "on_sale"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    MOVED = "moved"
    COMPLETED = "completed"


class Event(UUIDPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "events"
    __table_args__ = (Index("ix_events_status_starts_at", "status", "starts_at"),)

    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, default=None)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_min: Mapped[int | None] = mapped_column(Integer, default=None)
    age_rating: Mapped[str | None] = mapped_column(String(32), default=None)
    venue: Mapped[str | None] = mapped_column(String(255), default=None)
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=None)
    status: Mapped[EventStatus] = mapped_column(
        Enum(
            EventStatus,
            native_enum=False,
            length=16,
            values_callable=enum_values,
        ),
        default=EventStatus.DRAFT,
    )
    banner_small_url: Mapped[str | None] = mapped_column(String(512), default=None)
    banner_large_url: Mapped[str | None] = mapped_column(String(512), default=None)
    show_free_tickets: Mapped[bool] = mapped_column(Boolean, default=False)
    sale_paused: Mapped[bool] = mapped_column(Boolean, default=False)
    cloned_from_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("events.id"), default=None
    )

    ticket_types: Mapped[list["TicketType"]] = relationship(back_populates="event")


class TicketType(UUIDPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "ticket_types"
    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_ticket_types_price_non_negative"),
        CheckConstraint("quota >= 0", name="ck_ticket_types_quota_non_negative"),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    quota: Mapped[int]

    event: Mapped["Event"] = relationship(back_populates="ticket_types")
