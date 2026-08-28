"""Admin system-settings endpoints (S-8)."""

from typing import Annotated

from fastapi import APIRouter, Depends

from booking.core.deps import SettingsServiceDep, require_role
from booking.core.dto import Principal
from booking.models.users import RoleCode
from booking.schemas.admin_settings import SettingRead, SettingSet

AdminOnly = Annotated[Principal, Depends(require_role(RoleCode.ADMIN))]

router = APIRouter(prefix="/api/v1/admin/settings", tags=["admin:settings"])


@router.get(
    "",
    summary="List settings",
    description="List all admin-managed system settings.",
    response_model=list[SettingRead],
)
async def list_settings(
    service: SettingsServiceDep,
    _principal: AdminOnly,
) -> list[SettingRead]:
    return [SettingRead.from_setting(s) for s in await service.list()]


@router.get(
    "/{key}",
    summary="Get a setting",
    description="Return a single setting by its key.",
    response_model=SettingRead,
)
async def get_setting(
    key: str,
    service: SettingsServiceDep,
    _principal: AdminOnly,
) -> SettingRead:
    return SettingRead.from_setting(await service.get(key))


@router.put(
    "/{key}",
    summary="Set a setting",
    description="Create or update a setting value (stored as JSON).",
    response_model=SettingRead,
)
async def set_setting(
    key: str,
    body: SettingSet,
    service: SettingsServiceDep,
    _principal: AdminOnly,
) -> SettingRead:
    setting = await service.set(
        key=key,
        value=body.value,
        description=body.description,
        updated_by=_principal.user_id,
        actor=_principal,
    )
    return SettingRead.from_setting(setting)
