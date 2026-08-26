import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from booking.models.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPkMixin,
    VersionedMixin,
)


class Client(UUIDPkMixin, TimestampMixin, SoftDeleteMixin, VersionedMixin, Base):
    __tablename__ = "clients"

    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(32), default=None)
    full_name: Mapped[str | None] = mapped_column(String(255), default=None)
    discount_percent: Mapped[int]
    special_conditions: Mapped[str | None] = mapped_column(String(1024), default=None)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )


class UserType(enum.StrEnum):
    CLIENT = "client"
    SYSTEM_USER = "system_user"


class RefreshToken(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "refresh_tokens"

    user_type: Mapped[UserType] = mapped_column(String(16), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(), index=True)
    jti: Mapped[uuid.UUID] = mapped_column(Uuid(), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
