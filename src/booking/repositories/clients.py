from collections.abc import Sequence

from sqlalchemy import func, select

from booking.models.clients import Client
from booking.repositories.base import BaseRepository


class ClientRepository(BaseRepository[Client]):
    model = Client

    async def get_by_email(self, email: str) -> Client | None:
        stmt = self._base_select().where(Client.email == email)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(
        self, *, limit: int = 50, offset: int = 0
    ) -> tuple[Sequence[Client], int]:
        condition = Client.deleted_at.is_(None)
        stmt = (
            self._base_select()
            .where(condition)
            .order_by(Client.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        items = (await self._session.execute(stmt)).scalars().all()
        total_stmt = select(func.count()).select_from(Client).where(condition)
        total: int = (await self._session.execute(total_stmt)).scalar_one()
        return items, total
