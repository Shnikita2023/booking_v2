"""Public event catalogue reads and price synchronisation."""

import uuid
from collections.abc import Sequence

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from booking.core.errors import AppError
from booking.models.clients import InfoPage
from booking.models.events import Event
from booking.repositories.event import EventRepository, InfoPageRepository


class EventService:
    def __init__(self, session: AsyncSession) -> None:
        self._events = EventRepository(session)
        self._pages = InfoPageRepository(session)

    async def list_on_sale(self, *, limit: int, offset: int) -> tuple[list[Event], int]:
        events, total = await self._events.list_on_sale(limit=limit, offset=offset)
        return list(events), total

    async def get_public(self, event_id: uuid.UUID) -> Event:
        event = await self._events.get_on_sale(event_id)
        if event is None:
            raise AppError(
                "Event not found", code="event_not_found", status_code=status.HTTP_404_NOT_FOUND
            )
        return event

    async def sync_price(self, event: Event) -> Event:
        """Recompute the display price from active ticket types (source of truth)."""
        min_price = await self._events.active_min_price(event.id)
        await self._events.update(event, price=min_price)
        return event

    async def count_free_tickets(self, event: Event) -> int | None:
        if not event.show_free_tickets:
            return None
        return await self._events.free_tickets(event.id)

    async def count_free_tickets_bulk(
        self, events: Sequence[Event]
    ) -> dict[uuid.UUID, int | None]:
        """Free-ticket counts for many events in one query (no N+1 in the list)."""
        enabled_ids = [event.id for event in events if event.show_free_tickets]
        counts = await self._events.free_tickets_bulk(enabled_ids)
        return {
            event.id: (counts.get(event.id) if event.show_free_tickets else None)
            for event in events
        }

    async def get_page(self, slug: str) -> InfoPage:
        page = await self._pages.get_by_slug(slug)
        if page is None:
            raise AppError(
                "Page not found", code="page_not_found", status_code=status.HTTP_404_NOT_FOUND
            )
        return page
