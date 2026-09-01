"""Discount model: global and per-client/promo discounts (S-4)."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from booking.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPkMixin


class DiscountType(enum.StrEnum):
    GLOBAL = "global"
    EVENT = "event"
    CLIENT = "client"


class Discount(UUIDPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "discounts"

    name: Mapped[str] = mapped_column(String(128))
    percent: Mapped[int] = mapped_column(Integer)
    discount_type: Mapped[DiscountType] = mapped_column(
        String(16),
        default=DiscountType.GLOBAL,
    )
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("events.id"), default=None, index=True
    )
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("clients.id"), default=None, index=True
    )
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
