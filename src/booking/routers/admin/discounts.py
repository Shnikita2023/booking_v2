"""Admin discount endpoints (S-4): CRUD for global and per-client discounts."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from booking.core.deps import SessionDep, require_role
from booking.core.dto import Principal
from booking.models.users import RoleCode
from booking.schemas.discount import (
    DiscountCreate,
    DiscountListResponse,
    DiscountRead,
    DiscountUpdate,
)
from booking.services.discount_service import DiscountService

AdminManager = Annotated[Principal, Depends(require_role(RoleCode.ADMIN, RoleCode.MANAGER))]

router = APIRouter(prefix="/api/v1/admin/discounts", tags=["admin-discounts"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create a discount",
    description="Create a new global, event-specific, or client-specific discount.",
    response_model=DiscountRead,
)
async def create_discount(
    body: DiscountCreate,
    session: SessionDep,
    _principal: AdminManager,
) -> DiscountRead:
    svc = DiscountService(session)
    discount = await svc.create(body)
    return DiscountRead.from_discount(discount)


@router.get(
    "",
    summary="List discounts",
    description="List all discounts with pagination.",
    response_model=DiscountListResponse,
)
async def list_discounts(
    session: SessionDep,
    _principal: AdminManager,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DiscountListResponse:
    svc = DiscountService(session)
    items = await svc.list_all(limit=limit, offset=offset)
    return DiscountListResponse(
        items=[DiscountRead.from_discount(d) for d in items],
        total=len(items),
    )


@router.get(
    "/{discount_id}",
    summary="Get a discount",
    description="Get a single discount by ID.",
    response_model=DiscountRead,
)
async def get_discount(
    discount_id: uuid.UUID,
    session: SessionDep,
    _principal: AdminManager,
) -> DiscountRead:
    svc = DiscountService(session)
    discount = await svc.get(discount_id)
    return DiscountRead.from_discount(discount)


@router.put(
    "/{discount_id}",
    summary="Update a discount",
    description="Update discount fields.",
    response_model=DiscountRead,
)
async def update_discount(
    discount_id: uuid.UUID,
    body: DiscountUpdate,
    session: SessionDep,
    _principal: AdminManager,
) -> DiscountRead:
    svc = DiscountService(session)
    discount = await svc.update(discount_id, body)
    return DiscountRead.from_discount(discount)


@router.delete(
    "/{discount_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a discount",
    description="Soft-delete a discount.",
    response_model=None,
)
async def delete_discount(
    discount_id: uuid.UUID,
    session: SessionDep,
    _principal: AdminManager,
) -> None:
    svc = DiscountService(session)
    await svc.delete(discount_id)
