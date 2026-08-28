"""Repository for admin-managed system settings (key/value store)."""

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select

from booking.models.settings import SystemSetting
from booking.repositories.base import BaseRepository


class SystemSettingRepository(BaseRepository[SystemSetting]):
    model = SystemSetting

    async def get_by_key(self, key: str) -> SystemSetting | None:
        stmt = select(SystemSetting).where(SystemSetting.key == key)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self, *, limit: int = 50, offset: int = 0
    ) -> Sequence[SystemSetting]:
        stmt = select(SystemSetting).order_by(SystemSetting.key).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def set(
        self,
        *,
        key: str,
        value: Any,
        description: str | None,
        updated_by: uuid.UUID | None,
    ) -> SystemSetting:
        setting = await self.get_by_key(key)
        if setting is None:
            setting = SystemSetting(key=key)
            self._session.add(setting)
        setting.value = value
        setting.description = description
        setting.updated_by = updated_by
        await self._session.flush()
        return setting
