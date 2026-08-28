"""Admin management of system-wide settings stored as key/value JSON."""

import uuid
from collections.abc import Sequence
from typing import Any

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from booking.core.dto import Principal
from booking.core.errors import AppError
from booking.models.audit import AuditAction
from booking.models.settings import SystemSetting
from booking.repositories.settings import SystemSettingRepository
from booking.services.audit_service import AuditService


class SettingsService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settings = SystemSettingRepository(session)
        self._audit = AuditService(session)

    async def list(self) -> Sequence[SystemSetting]:
        return await self._settings.list()

    async def get(self, key: str) -> SystemSetting:
        setting = await self._settings.get_by_key(key)
        if setting is None:
            raise AppError(
                "Setting not found",
                code="setting_not_found",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return setting

    async def set(
        self,
        *,
        key: str,
        value: Any,
        description: str | None = None,
        updated_by: uuid.UUID | None = None,
        actor: Principal | None = None,
    ) -> SystemSetting:
        setting = await self._settings.set(
            key=key, value=value, description=description, updated_by=updated_by
        )
        await self._audit.record(
            action=AuditAction.SETTINGS_SET,
            entity_type="system_setting",
            entity_id=None,
            actor=actor,
            payload={"key": key},
        )
        await self._session.commit()
        return setting
