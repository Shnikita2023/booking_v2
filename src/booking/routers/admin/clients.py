"""Admin client management endpoints (S-3)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from booking.core.deps import ClientAdminServiceDep, require_role
from booking.core.dto import Principal
from booking.models.users import RoleCode
from booking.schemas.admin_clients import (
    ClientCreate,
    ClientListResponse,
    ClientRead,
    ClientUpdate,
    PasswordReset,
)

AdminManager = Annotated[Principal, Depends(require_role(RoleCode.ADMIN, RoleCode.MANAGER))]

router = APIRouter(prefix="/api/v1/admin/clients", tags=["admin:clients"])


@router.post(
    "",
    summary="Create a client",
    description="Create a client account (active by default).",
    response_model=ClientRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_client(
    body: ClientCreate,
    service: ClientAdminServiceDep,
    _principal: AdminManager,
) -> ClientRead:
    client = await service.create(
        email=body.email,
        full_name=body.full_name,
        phone=body.phone,
        password=body.password,
        discount_percent=body.discount_percent,
        actor=_principal,
    )
    return ClientRead.from_client(client)


@router.get(
    "",
    summary="List clients",
    description="List client accounts (excluding soft-deleted), paginated.",
    response_model=ClientListResponse,
)
async def list_clients(
    service: ClientAdminServiceDep,
    _principal: AdminManager,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ClientListResponse:
    clients, total = await service.list_all(limit=limit, offset=offset)
    return ClientListResponse(items=[ClientRead.from_client(c) for c in clients], total=total)


@router.get(
    "/{client_id}",
    summary="Get a client",
    description="Return a single client by id.",
    response_model=ClientRead,
)
async def get_client(
    client_id: uuid.UUID,
    service: ClientAdminServiceDep,
    _principal: AdminManager,
) -> ClientRead:
    return ClientRead.from_client(await service.get(client_id))


@router.put(
    "/{client_id}",
    summary="Update a client",
    description="Update mutable client fields (name, phone, discount).",
    response_model=ClientRead,
)
async def update_client(
    client_id: uuid.UUID,
    body: ClientUpdate,
    service: ClientAdminServiceDep,
    _principal: AdminManager,
) -> ClientRead:
    client = await service.update(
        client_id, actor=_principal, **body.model_dump(exclude_unset=True)
    )
    return ClientRead.from_client(client)


@router.post(
    "/{client_id}/reset-password",
    summary="Reset client password",
    description="Force-reset a client's password.",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def reset_client_password(
    client_id: uuid.UUID,
    body: PasswordReset,
    service: ClientAdminServiceDep,
    _principal: AdminManager,
) -> None:
    await service.reset_password(client_id, body.password, actor=_principal)


@router.post(
    "/{client_id}/block",
    summary="Block a client",
    description="Deactivate a client account (is_active=False).",
    response_model=ClientRead,
)
async def block_client(
    client_id: uuid.UUID,
    service: ClientAdminServiceDep,
    _principal: AdminManager,
) -> ClientRead:
    return ClientRead.from_client(await service.block(client_id, actor=_principal))


@router.post(
    "/{client_id}/unblock",
    summary="Unblock a client",
    description="Reactivate a client account (is_active=True).",
    response_model=ClientRead,
)
async def unblock_client(
    client_id: uuid.UUID,
    service: ClientAdminServiceDep,
    _principal: AdminManager,
) -> ClientRead:
    return ClientRead.from_client(await service.unblock(client_id, actor=_principal))


@router.delete(
    "/{client_id}",
    summary="Delete a client",
    description="Soft-delete a client account.",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_client(
    client_id: uuid.UUID,
    service: ClientAdminServiceDep,
    _principal: AdminManager,
) -> None:
    await service.delete(client_id, actor=_principal)
