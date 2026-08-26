from booking.models.clients import Client
from booking.repositories.base import BaseRepository


class ClientRepository(BaseRepository[Client]):
    model = Client

    async def get_by_email(self, email: str) -> Client | None:
        stmt = self._base_select().where(Client.email == email)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
