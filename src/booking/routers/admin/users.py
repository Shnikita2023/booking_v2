"""Admin system-user (staff) management endpoints (S-8)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from booking.core.deps import SystemUserAdminServiceDep, require_role
from booking.core.dto import Principal
from booking.models.users import RoleCode
from booking.schemas.admin_users import (
    PasswordReset,
    UserCreate,
    UserListResponse,
    UserRead,
    UserUpdate,
)

AdminOnly = Annotated[Principal, Depends(require_role(RoleCode.ADMIN))]

router = APIRouter(prefix="/api/v1/admin/users", tags=["admin:users"])


@router.post(
    "",
    summary="Create a system user",
    description="Create a staff account with the given role (seeds the role if missing).",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    body: UserCreate,
    service: SystemUserAdminServiceDep,
    _principal: AdminOnly,
) -> UserRead:
    user = await service.create(
        email=body.email, password=body.password, role_code=body.role_code, actor=_principal
    )
    return UserRead.from_user(user)


@router.get(
    "",
    summary="List system users",
    description="List staff accounts (excluding soft-deleted), paginated.",
    response_model=UserListResponse,
)
async def list_users(
    service: SystemUserAdminServiceDep,
    _principal: AdminOnly,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> UserListResponse:
    users, total = await service.list_all(limit=limit, offset=offset)
    return UserListResponse(items=[UserRead.from_user(u) for u in users], total=total)


@router.get(
    "/{user_id}",
    summary="Get a system user",
    description="Return a single staff account by id.",
    response_model=UserRead,
)
async def get_user(
    user_id: uuid.UUID,
    service: SystemUserAdminServiceDep,
    _principal: AdminOnly,
) -> UserRead:
    return UserRead.from_user(await service.get(user_id))


@router.put(
    "/{user_id}",
    summary="Update a system user",
    description="Update staff fields: full_name, role_code and/or is_active.",
    response_model=UserRead,
)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    service: SystemUserAdminServiceDep,
    _principal: AdminOnly,
) -> UserRead:
    changes = body.model_dump(exclude_unset=True)
    user = await service.update(user_id, actor=_principal, **changes)
    return UserRead.from_user(user)


@router.post(
    "/{user_id}/reset-password",
    summary="Reset system user password",
    description="Force-reset a staff account password.",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def reset_user_password(
    user_id: uuid.UUID,
    body: PasswordReset,
    service: SystemUserAdminServiceDep,
    _principal: AdminOnly,
) -> None:
    await service.reset_password(user_id, body.password, actor=_principal)


@router.post(
    "/{user_id}/block",
    summary="Block a system user",
    description="Deactivate a staff account (is_active=False).",
    response_model=UserRead,
)
async def block_user(
    user_id: uuid.UUID,
    service: SystemUserAdminServiceDep,
    _principal: AdminOnly,
) -> UserRead:
    return UserRead.from_user(await service.block(user_id, actor=_principal))


@router.post(
    "/{user_id}/unblock",
    summary="Unblock a system user",
    description="Reactivate a staff account (is_active=True).",
    response_model=UserRead,
)
async def unblock_user(
    user_id: uuid.UUID,
    service: SystemUserAdminServiceDep,
    _principal: AdminOnly,
) -> UserRead:
    return UserRead.from_user(await service.unblock(user_id, actor=_principal))


@router.delete(
    "/{user_id}",
    summary="Delete a system user",
    description="Soft-delete a staff account.",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_user(
    user_id: uuid.UUID,
    service: SystemUserAdminServiceDep,
    _principal: AdminOnly,
) -> None:
    await service.delete(user_id, actor=_principal)
