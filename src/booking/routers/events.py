import uuid

from fastapi import APIRouter, Query

from booking.core.deps import SessionDep
from booking.schemas.event import (
    EventDetail,
    EventListResponse,
    EventShort,
    ListQuery,
)
from booking.services.event_service import EventService

router = APIRouter(prefix="/api/v1/events", tags=["events"])


@router.get("")
async def list_events(
    session: SessionDep,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> EventListResponse:
    query = ListQuery(limit=limit, offset=offset)
    service = EventService(session)
    events, total = await service.list_on_sale(
        limit=query.limit, offset=query.offset
    )
    items = [
        EventShort(
            id=event.id,
            title=event.title,
            starts_at=event.starts_at,
            venue=event.venue,
            age_rating=event.age_rating,
            banner_small_url=event.banner_small_url,
            free_tickets=await service.count_free_tickets(event),
        )
        for event in events
    ]
    return EventListResponse(items=items, total=total)


@router.get("/{event_id}")
async def get_event(event_id: uuid.UUID, session: SessionDep) -> EventDetail:
    event = await EventService(session).get_public(event_id)
    return EventDetail(
        id=event.id,
        title=event.title,
        description=event.description,
        starts_at=event.starts_at,
        duration_min=event.duration_min,
        age_rating=event.age_rating,
        venue=event.venue,
        price=event.price,
        status=event.status.value,
        banner_small_url=event.banner_small_url,
        banner_large_url=event.banner_large_url,
        show_free_tickets=event.show_free_tickets,
        sale_paused=event.sale_paused,
        free_tickets=await EventService(session).count_free_tickets(event),
    )
