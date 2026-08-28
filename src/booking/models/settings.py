"""System settings key/value store (admin-managed configuration)."""

import uuid
from typing import Any

from sqlalchemy import String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from booking.models.base import Base, TimestampMixin


class SystemSetting(TimestampMixin, Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[Any] = mapped_column(JSONB, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(), default=None)
