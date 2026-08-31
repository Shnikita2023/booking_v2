import uuid
from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import func, select

from booking.models.clients import InfoPage
from booking.models.events import Event, EventStatus, TicketType
from booking.repositories.base import BaseRepository


class EventRepository(BaseRepository[Event]):
    model = Event

    async def list_on_sale(
        self, *, limit: int = 20, offset: int = 0
    ) -> tuple[Sequence[Event], int]:
        condition = (Event.status == EventStatus.ON_SALE) & Event.deleted_at.is_(None)
        stmt = (
            select(Event)
            .where(condition)
            .order_by(Event.starts_at)
            .limit(limit)
            .offset(offset)
        )
        count_stmt = select(func.count()).select_from(Event).where(condition)
        events = (await self._session.execute(stmt)).scalars().all()
        total = (await self._session.execute(count_stmt)).scalar_one()
        return events, total

    async def get_on_sale(self, event_id: uuid.UUID) -> Event | None:
        stmt = select(Event).where(
            Event.id == event_id,
            Event.status == EventStatus.ON_SALE,
            Event.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_any(self, event_id: uuid.UUID) -> Event | None:
        stmt = self._base_select().where(Event.id == event_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(
        self, *, limit: int = 50, offset: int = 0
    ) -> tuple[Sequence[Event], int]:
        condition = Event.deleted_at.is_(None)
        stmt = (
            self._base_select()
            .where(condition)
            .order_by(Event.starts_at)
            .limit(limit)
            .offset(offset)
        )
        count_stmt = select(func.count()).select_from(Event).where(condition)
        events = (await self._session.execute(stmt)).scalars().all()
        total = (await self._session.execute(count_stmt)).scalar_one()
        return events, total

    async def active_min_price(self, event_id: uuid.UUID) -> Decimal | None:
        """Source of truth for the display price: cheapest active ticket type."""
        stmt = select(func.min(TicketType.price)).where(
            TicketType.event_id == event_id,
            TicketType.deleted_at.is_(None),
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_with_min_price(
        self, event_id: uuid.UUID
    ) -> tuple[Event | None, Decimal | None]:
        """Return the event together with its cheapest active ticket-type price."""
        stmt = (
            select(Event, func.min(TicketType.price))
            .outerjoin(
                TicketType,
                (TicketType.event_id == Event.id) & (TicketType.deleted_at.is_(None)),
            )
            .where(Event.id == event_id, Event.deleted_at.is_(None))
            .group_by(Event.id)
        )
        row = (await self._session.execute(stmt)).first()
        if row is None:
            return None, None
        return row[0], row[1]

    async def free_tickets(self, event_id: uuid.UUID) -> int:
        stmt = select(
            func.coalesce(func.sum(TicketType.quota - TicketType.sold), 0)
        ).where(
            TicketType.event_id == event_id,
            TicketType.deleted_at.is_(None),
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def free_tickets_bulk(
        self, event_ids: Sequence[uuid.UUID]
    ) -> dict[uuid.UUID, int]:
        """Free-ticket counts per event in a single grouped query (avoids N+1)."""
        if not event_ids:
            return {}
        stmt = select(
            TicketType.event_id,
            func.coalesce(func.sum(TicketType.quota - TicketType.sold), 0),
        ).where(
            TicketType.event_id.in_(event_ids),
            TicketType.deleted_at.is_(None),
        ).group_by(TicketType.event_id)
        rows = (await self._session.execute(stmt)).all()
        return {row[0]: int(row[1]) for row in rows}


class InfoPageRepository(BaseRepository[InfoPage]):
    model = InfoPage

    async def get_by_slug(self, slug: str) -> InfoPage | None:
        stmt = self._base_select().where(InfoPage.slug == slug)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()


class TicketTypeRepository(BaseRepository[TicketType]):
    model = TicketType

    async def lock(self, ticket_type_id: uuid.UUID) -> TicketType | None:
        """Row-level lock (FOR UPDATE) for atomic quota updates under concurrency."""
        stmt = (
            select(TicketType)
            .where(TicketType.id == ticket_type_id)
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def lock_skip_locked(self, ticket_type_id: uuid.UUID) -> TicketType | None:
        """Row-level lock (FOR UPDATE SKIP LOCKED) for cleanup to avoid deadlocks."""
        stmt = (
            select(TicketType)
            .where(TicketType.id == ticket_type_id)
            .with_for_update(skip_locked=True)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_event(self, event_id: uuid.UUID) -> Sequence[TicketType]:
        stmt = (
            self._base_select()
            .where(TicketType.event_id == event_id)
            .order_by(TicketType.name)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_by_event(
        self, ticket_type_id: uuid.UUID, event_id: uuid.UUID
    ) -> TicketType | None:
        """Return a ticket type only if it belongs to the given event."""
        stmt = self._base_select().where(
            TicketType.id == ticket_type_id,
            TicketType.event_id == event_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
