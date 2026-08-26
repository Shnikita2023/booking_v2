import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from booking.models.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPkMixin,
)


class RoleCode(enum.StrEnum):
    ADMIN = "admin"
    MANAGER = "manager"
    CASHIER = "cashier"


class Role(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "roles"

    code: Mapped[RoleCode] = mapped_column(
        Enum(
            RoleCode,
            native_enum=False,
            length=32,
            values_callable=lambda e: [m.value for m in e],
        ),
        unique=True,
    )
    name: Mapped[str] = mapped_column(String(128))

    users: Mapped[list["SystemUser"]] = relationship(back_populates="role")


class SystemUser(UUIDPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "system_users"

    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(255), default=None)
    role_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("roles.id"), index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    active_session_id: Mapped[uuid.UUID | None] = mapped_column(default=None)

    role: Mapped[Role] = relationship(back_populates="users")
