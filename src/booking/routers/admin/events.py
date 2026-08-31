"""Admin event management endpoints (S-2)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from booking.core.deps import EventAdminServiceDep, require_role
from booking.core.dto import Principal, TicketTypeSeed
from booking.models.users import RoleCode
from booking.schemas.admin_events import (
    EventCreate,
    EventListResponse,
    EventMove,
    EventRead,
    EventUpdate,
    TicketTypeCreate,
    TicketTypeListResponse,
    TicketTypeRead,
    TicketTypeUpdate,
)

AdminManager = Annotated[Principal, Depends(require_role(RoleCode.ADMIN, RoleCode.MANAGER))]

router = APIRouter(prefix="/api/v1/admin/events", tags=["admin:events"])


@router.post(
    "",
    summary="Create an event",
    description="Create a new event in DRAFT status with optional ticket types. "
    "Price is derived from the cheapest active ticket type.",
    response_model=EventRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_event(
    body: EventCreate,
    service: EventAdminServiceDep,
    _principal: AdminManager,
) -> EventRead:
    seeds = (
        [TicketTypeSeed(**s.model_dump()) for s in body.ticket_types]
        if body.ticket_types
        else None
    )
    event = await service.create(
        title=body.title,
        description=body.description,
        starts_at=body.starts_at,
        duration_min=body.duration_min,
        age_rating=body.age_rating,
        venue=body.venue,
        banner_small_url=body.banner_small_url,
        banner_large_url=body.banner_large_url,
        show_free_tickets=body.show_free_tickets,
        sale_paused=body.sale_paused,
        ticket_types=seeds,
        actor=_principal,
    )
    return EventRead.from_event(event)


@router.get(
    "",
    summary="List events",
    description="List all events regardless of status (admin view), paginated.",
    response_model=EventListResponse,
)
async def list_events(
    service: EventAdminServiceDep,
    _principal: AdminManager,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> EventListResponse:
    events, total = await service.list_all(limit=limit, offset=offset)
    return EventListResponse(items=[EventRead.from_event(e) for e in events], total=total)


@router.get(
    "/{event_id}",
    summary="Get an event",
    description="Return a single event by id in any status.",
    response_model=EventRead,
)
async def get_event(
    event_id: uuid.UUID,
    service: EventAdminServiceDep,
    _principal: AdminManager,
) -> EventRead:
    return EventRead.from_event(await service.get(event_id))


@router.get(
    "/{event_id}/ticket-types",
    summary="List ticket types",
    description="List ticket types for an event.",
    response_model=TicketTypeListResponse,
)
async def list_ticket_types(
    event_id: uuid.UUID,
    service: EventAdminServiceDep,
    _principal: AdminManager,
) -> TicketTypeListResponse:
    ticket_types = await service.list_ticket_types(event_id)
    return TicketTypeListResponse(items=[TicketTypeRead.from_ticket_type(t) for t in ticket_types])


@router.put(
    "/{event_id}",
    summary="Update an event",
    description="Update mutable event fields. Status and price are managed by dedicated actions.",
    response_model=EventRead,
)
async def update_event(
    event_id: uuid.UUID,
    body: EventUpdate,
    service: EventAdminServiceDep,
    _principal: AdminManager,
) -> EventRead:
    event = await service.update(event_id, actor=_principal, **body.model_dump(exclude_unset=True))
    return EventRead.from_event(event)


@router.post(
    "/{event_id}/clone",
    summary="Clone an event",
    description="Create a DRAFT copy of an event with its ticket types (sold reset to 0).",
    response_model=EventRead,
    status_code=status.HTTP_201_CREATED,
)
async def clone_event(
    event_id: uuid.UUID,
    service: EventAdminServiceDep,
    _principal: AdminManager,
) -> EventRead:
    return EventRead.from_event(await service.clone(event_id, actor=_principal))


@router.post(
    "/{event_id}/publish",
    summary="Publish an event",
    description="Move an event to ON_SALE.",
    response_model=EventRead,
)
async def publish_event(
    event_id: uuid.UUID,
    service: EventAdminServiceDep,
    _principal: AdminManager,
) -> EventRead:
    return EventRead.from_event(await service.publish(event_id, actor=_principal))


@router.post(
    "/{event_id}/cancel",
    summary="Cancel an event",
    description="Cancel an event (status CANCELLED).",
    response_model=EventRead,
)
async def cancel_event(
    event_id: uuid.UUID,
    service: EventAdminServiceDep,
    _principal: AdminManager,
) -> EventRead:
    return EventRead.from_event(await service.cancel(event_id, actor=_principal))


@router.post(
    "/{event_id}/complete",
    summary="Complete an event",
    description="Mark an event as COMPLETED.",
    response_model=EventRead,
)
async def complete_event(
    event_id: uuid.UUID,
    service: EventAdminServiceDep,
    _principal: AdminManager,
) -> EventRead:
    return EventRead.from_event(await service.complete(event_id, actor=_principal))


@router.post(
    "/{event_id}/pause-sales",
    summary="Pause sales",
    description="Pause ticket sales for an event without changing its status.",
    response_model=EventRead,
)
async def pause_sales(
    event_id: uuid.UUID,
    service: EventAdminServiceDep,
    _principal: AdminManager,
) -> EventRead:
    return EventRead.from_event(await service.pause_sales(event_id, actor=_principal))


@router.post(
    "/{event_id}/resume-sales",
    summary="Resume sales",
    description="Resume ticket sales for an event.",
    response_model=EventRead,
)
async def resume_sales(
    event_id: uuid.UUID,
    service: EventAdminServiceDep,
    _principal: AdminManager,
) -> EventRead:
    return EventRead.from_event(await service.resume_sales(event_id, actor=_principal))


@router.post(
    "/{event_id}/move",
    summary="Move an event",
    description="Change the event start time and set status to MOVED.",
    response_model=EventRead,
)
async def move_event(
    event_id: uuid.UUID,
    body: EventMove,
    service: EventAdminServiceDep,
    _principal: AdminManager,
) -> EventRead:
    return EventRead.from_event(await service.move(event_id, body.starts_at, actor=_principal))


@router.post(
    "/{event_id}/ticket-types",
    summary="Create a ticket type",
    description="Add a ticket type to an event. Price is re-synced afterwards.",
    response_model=TicketTypeRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_ticket_type(
    event_id: uuid.UUID,
    body: TicketTypeCreate,
    service: EventAdminServiceDep,
    _principal: AdminManager,
) -> TicketTypeRead:
    ticket_type = await service.create_ticket_type(
        event_id, name=body.name, price=body.price, quota=body.quota, actor=_principal
    )
    return TicketTypeRead.from_ticket_type(ticket_type)


@router.put(
    "/{event_id}/ticket-types/{ticket_type_id}",
    summary="Update a ticket type",
    description="Update a ticket type. Quota cannot be lowered below sold tickets (409).",
    response_model=TicketTypeRead,
)
async def update_ticket_type(
    event_id: uuid.UUID,
    ticket_type_id: uuid.UUID,
    body: TicketTypeUpdate,
    service: EventAdminServiceDep,
    _principal: AdminManager,
) -> TicketTypeRead:
    ticket_type = await service.update_ticket_type(
        ticket_type_id, event_id=event_id, actor=_principal, **body.model_dump(exclude_unset=True)
    )
    return TicketTypeRead.from_ticket_type(ticket_type)


@router.delete(
    "/{event_id}/ticket-types/{ticket_type_id}",
    summary="Delete a ticket type",
    description="Soft-delete a ticket type. Cannot delete one with sales (409).",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_ticket_type(
    event_id: uuid.UUID,
    ticket_type_id: uuid.UUID,
    service: EventAdminServiceDep,
    _principal: AdminManager,
) -> None:
    await service.delete_ticket_type(ticket_type_id, event_id=event_id, actor=_principal)
