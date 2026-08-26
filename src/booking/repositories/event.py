import uuid
from collections.abc import Sequence

from sqlalchemy import func, select

from booking.models.clients import InfoPage
from booking.models.events import Event, EventStatus
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


class InfoPageRepository(BaseRepository[InfoPage]):
    model = InfoPage

    async def get_by_slug(self, slug: str) -> InfoPage | None:
        stmt = self._base_select().where(InfoPage.slug == slug)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
