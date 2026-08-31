"""Stub mailer that persists emails to email_outbox table (D-8)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from booking.messaging.mailer import EmailMessage
from booking.models.email_outbox import EmailOutbox


class StubMailer:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def send(
        self, *, to: str, subject: str, body: str, template: str
    ) -> EmailMessage:
        msg = EmailMessage(to=to, subject=subject, body=body, template=template)
        self._session.add(
            EmailOutbox(
                id=uuid.uuid4(),
                to=to,
                subject=subject,
                body=body,
                template=template,
                status="PENDING",
                created_at=datetime.now(UTC),
            )
        )
        await self._session.flush()
        return msg
