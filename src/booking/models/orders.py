import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from booking.models.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPkMixin,
    VersionedMixin,
)
from booking.models.events import enum_values


class OrderStatus(enum.StrEnum):
    RESERVED = "reserved"
    PAID = "paid"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class TicketStatus(enum.StrEnum):
    ACTIVE = "active"
    CANCELLED = "cancelled"


class PaymentStatus(enum.StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"


class Order(UUIDPkMixin, TimestampMixin, SoftDeleteMixin, VersionedMixin, Base):
    __tablename__ = "orders"

    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), index=True)
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"), index=True)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(
            OrderStatus,
            native_enum=False,
            length=16,
            values_callable=enum_values,
        ),
        default=OrderStatus.RESERVED,
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    reserved_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )

    tickets: Mapped[list["Ticket"]] = relationship(back_populates="order")


class Ticket(UUIDPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "tickets"
    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_tickets_price_non_negative"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), index=True)
    ticket_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ticket_types.id"), index=True
    )
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[TicketStatus] = mapped_column(
        Enum(
            TicketStatus,
            native_enum=False,
            length=16,
            values_callable=enum_values,
        ),
        default=TicketStatus.ACTIVE,
    )

    order: Mapped["Order"] = relationship(back_populates="tickets")


class Payment(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "payments"

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), index=True)
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(
            PaymentStatus,
            native_enum=False,
            length=16,
            values_callable=enum_values,
        ),
        default=PaymentStatus.PENDING,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    external_id: Mapped[str | None] = mapped_column(String(255), default=None)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), default=None, index=True)
    method: Mapped[str] = mapped_column(String(16), default="card")
    currency: Mapped[str] = mapped_column(String(8), default="RUB")
    gateway: Mapped[str] = mapped_column(String(32), default="mock")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
