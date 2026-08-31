"""Payment data access."""

import uuid

from sqlalchemy import select

from booking.models.orders import Payment, PaymentStatus
from booking.repositories.base import BaseRepository


class PaymentRepository(BaseRepository[Payment]):
    model = Payment

    async def get_by_order(self, order_id: uuid.UUID) -> Payment | None:
        stmt = self._base_select().where(Payment.order_id == order_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_external_id(self, external_id: str) -> Payment | None:
        stmt = (
            select(Payment)
            .where(Payment.external_id == external_id)
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(self, key: str) -> Payment | None:
        stmt = self._base_select().where(Payment.idempotency_key == key)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_status(
        self, payment: Payment, status: PaymentStatus, *, external_id: str | None = None
    ) -> Payment:
        payment.status = status
        if external_id is not None:
            payment.external_id = external_id
        await self._session.flush()
        return payment
