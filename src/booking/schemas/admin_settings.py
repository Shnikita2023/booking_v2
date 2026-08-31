"""Admin schemas for system-wide settings."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from booking.models.settings import SystemSetting


class SettingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    value: Any = None
    description: str | None = None
    updated_by: UUID | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_setting(cls, setting: SystemSetting) -> "SettingRead":
        return cls(
            key=setting.key,
            value=setting.value,
            description=setting.description,
            updated_by=setting.updated_by,
            created_at=setting.created_at,
            updated_at=setting.updated_at,
        )


class SettingSet(BaseModel):
    value: Any = None
    description: str | None = None
