"""Admin management of events, ticket types and lifecycle actions."""

import uuid
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from booking.core.dto import TicketTypeSeed
from booking.core.errors import AppError
from booking.models.events import Event, EventStatus, TicketType
from booking.repositories.event import EventRepository, TicketTypeRepository


class EventAdminService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._events = EventRepository(session)
        self._ticket_types = TicketTypeRepository(session)

    async def _sync_price(self, event_id: uuid.UUID) -> None:
        min_price = await self._events.active_min_price(event_id)
        event = await self._events.get_any(event_id)
        if event is not None:
            await self._events.update(event, price=min_price)

    async def create(
        self,
        *,
        title: str,
        description: str | None,
        starts_at: datetime,
        duration_min: int | None,
        age_rating: str | None,
        venue: str | None,
        banner_small_url: str | None,
        banner_large_url: str | None,
        show_free_tickets: bool,
        sale_paused: bool,
        ticket_types: list[TicketTypeSeed] | None,
    ) -> Event:
        event = await self._events.create(
            title=title,
            description=description,
            starts_at=starts_at,
            duration_min=duration_min,
            age_rating=age_rating,
            venue=venue,
            price=None,
            status=EventStatus.DRAFT,
            banner_small_url=banner_small_url,
            banner_large_url=banner_large_url,
            show_free_tickets=show_free_tickets,
            sale_paused=sale_paused,
        )
        if ticket_types:
            for seed in ticket_types:
                await self._ticket_types.create(
                    event_id=event.id,
                    name=seed.name,
                    price=seed.price,
                    quota=seed.quota,
                    sold=0,
                )
        await self._sync_price(event.id)
        await self._session.commit()
        return await self.get(event.id)

    async def update(self, event_id: uuid.UUID, **changes: Any) -> Event:
        event = await self._events.get_any(event_id)
        if event is None:
            raise AppError(
                "Event not found",
                code="event_not_found",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        if changes:
            await self._events.update(event, **changes)
        await self._session.commit()
        return await self.get(event_id)

    async def get(self, event_id: uuid.UUID) -> Event:
        event = await self._events.get_any(event_id)
        if event is None:
            raise AppError(
                "Event not found",
                code="event_not_found",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return event

    async def list_ticket_types(self, event_id: uuid.UUID) -> Sequence[TicketType]:
        await self.get(event_id)
        return await self._ticket_types.list_by_event(event_id)

    async def list_all(
        self, *, limit: int = 50, offset: int = 0
    ) -> tuple[Sequence[Event], int]:
        return await self._events.list_all(limit=limit, offset=offset)

    async def clone(self, event_id: uuid.UUID) -> Event:
        source = await self._events.get_any(event_id)
        if source is None:
            raise AppError(
                "Event not found",
                code="event_not_found",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        cloned = await self._events.create(
            title=source.title,
            description=source.description,
            starts_at=source.starts_at,
            duration_min=source.duration_min,
            age_rating=source.age_rating,
            venue=source.venue,
            price=source.price,
            status=EventStatus.DRAFT,
            banner_small_url=source.banner_small_url,
            banner_large_url=source.banner_large_url,
            show_free_tickets=source.show_free_tickets,
            sale_paused=source.sale_paused,
            cloned_from_id=source.id,
        )
        for tt in await self._ticket_types.list_by_event(source.id):
            await self._ticket_types.create(
                event_id=cloned.id,
                name=tt.name,
                price=tt.price,
                quota=tt.quota,
                sold=0,
            )
        await self._sync_price(cloned.id)
        await self._session.commit()
        return await self.get(cloned.id)

    async def _set_status(self, event_id: uuid.UUID, status_: EventStatus) -> Event:
        event = await self._events.get_any(event_id)
        if event is None:
            raise AppError(
                "Event not found",
                code="event_not_found",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        await self._events.update(event, status=status_)
        await self._session.commit()
        return await self.get(event_id)

    async def publish(self, event_id: uuid.UUID) -> Event:
        return await self._set_status(event_id, EventStatus.ON_SALE)

    async def cancel(self, event_id: uuid.UUID) -> Event:
        return await self._set_status(event_id, EventStatus.CANCELLED)

    async def complete(self, event_id: uuid.UUID) -> Event:
        return await self._set_status(event_id, EventStatus.COMPLETED)

    async def pause_sales(self, event_id: uuid.UUID) -> Event:
        event = await self._events.get_any(event_id)
        if event is None:
            raise AppError(
                "Event not found",
                code="event_not_found",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        await self._events.update(event, sale_paused=True)
        await self._session.commit()
        return await self.get(event_id)

    async def resume_sales(self, event_id: uuid.UUID) -> Event:
        event = await self._events.get_any(event_id)
        if event is None:
            raise AppError(
                "Event not found",
                code="event_not_found",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        await self._events.update(event, sale_paused=False)
        await self._session.commit()
        return await self.get(event_id)

    async def move(self, event_id: uuid.UUID, new_starts_at: datetime) -> Event:
        event = await self._events.get_any(event_id)
        if event is None:
            raise AppError(
                "Event not found",
                code="event_not_found",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        await self._events.update(event, status=EventStatus.MOVED, starts_at=new_starts_at)
        await self._session.commit()
        return await self.get(event_id)

    async def create_ticket_type(
        self, event_id: uuid.UUID, *, name: str, price: Decimal, quota: int
    ) -> TicketType:
        event = await self._events.get_any(event_id)
        if event is None:
            raise AppError(
                "Event not found",
                code="event_not_found",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        ticket_type = await self._ticket_types.create(
            event_id=event_id, name=name, price=price, quota=quota, sold=0
        )
        await self._sync_price(event_id)
        await self._session.commit()
        return ticket_type

    async def update_ticket_type(
        self, ticket_type_id: uuid.UUID, **changes: Any
    ) -> TicketType:
        ticket_type = await self._ticket_types.get(ticket_type_id)
        if ticket_type is None:
            raise AppError(
                "Ticket type not found",
                code="ticket_type_not_found",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        new_quota = changes.get("quota", ticket_type.quota)
        if new_quota < ticket_type.sold:
            raise AppError(
                "Quota below sold amount",
                code="quota_below_sold",
                status_code=status.HTTP_409_CONFLICT,
            )
        await self._ticket_types.update(ticket_type, **changes)
        await self._sync_price(ticket_type.event_id)
        await self._session.commit()
        return ticket_type

    async def delete_ticket_type(self, ticket_type_id: uuid.UUID) -> None:
        ticket_type = await self._ticket_types.get(ticket_type_id)
        if ticket_type is None:
            raise AppError(
                "Ticket type not found",
                code="ticket_type_not_found",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        if ticket_type.sold > 0:
            raise AppError(
                "Cannot delete a ticket type with sales",
                code="ticket_type_has_sales",
                status_code=status.HTTP_409_CONFLICT,
            )
        await self._ticket_types.soft_delete(ticket_type_id)
        await self._sync_price(ticket_type.event_id)
        await self._session.commit()
