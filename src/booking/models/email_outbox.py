"""Email outbox for outgoing mail (D-8)."""

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from booking.models.base import Base, UUIDPkMixin


class EmailOutbox(UUIDPkMixin, Base):
    __tablename__ = "email_outbox"

    to: Mapped[str] = mapped_column(String(255), index=True)
    subject: Mapped[str] = mapped_column(String(512))
    body: Mapped[str] = mapped_column(Text)
    template: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    error: Mapped[str | None] = mapped_column(Text, default=None)
