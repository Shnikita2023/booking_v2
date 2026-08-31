"""Email outbox data access."""

import uuid

from sqlalchemy import select

from booking.models.email_outbox import EmailOutbox
from booking.repositories.base import BaseRepository


class EmailOutboxRepository(BaseRepository[EmailOutbox]):
    model = EmailOutbox

    async def get_pending(self, limit: int = 50) -> list[EmailOutbox]:
        stmt = (
            select(EmailOutbox)
            .where(EmailOutbox.status == "PENDING")
            .order_by(EmailOutbox.created_at)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def mark_sent(self, email_id: uuid.UUID) -> None:
        email = await self.get(email_id)
        if email is not None:
            email.status = "SENT"
            await self._session.flush()
