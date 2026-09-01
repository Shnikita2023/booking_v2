"""Discount service: CRUD and effective discount calculation (S-4)."""

import uuid
from datetime import UTC, datetime

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from booking.core.errors import AppError
from booking.models.clients import Client
from booking.models.discounts import Discount, DiscountType
from booking.repositories.discounts import DiscountRepository
from booking.schemas.discount import DiscountCreate, DiscountUpdate


class DiscountService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = DiscountRepository(session)

    async def create(self, data: DiscountCreate) -> Discount:
        return await self._repo.create(
            name=data.name,
            percent=data.percent,
            discount_type=DiscountType(data.discount_type),
            event_id=data.event_id,
            client_id=data.client_id,
            valid_from=data.valid_from,
            valid_until=data.valid_until,
            is_active=data.is_active,
        )

    async def get(self, discount_id: uuid.UUID) -> Discount:
        discount = await self._repo.get(discount_id)
        if discount is None:
            raise AppError(
                "Discount not found",
                code="discount_not_found",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return discount

    async def list_all(self, *, limit: int = 50, offset: int = 0) -> list[Discount]:
        return list(await self._repo.list(limit=limit, offset=offset))

    async def update(self, discount_id: uuid.UUID, data: DiscountUpdate) -> Discount:
        discount = await self.get(discount_id)
        updates = data.model_dump(exclude_unset=True)
        return await self._repo.update(discount, **updates)

    async def delete(self, discount_id: uuid.UUID) -> None:
        if not await self._repo.soft_delete(discount_id):
            raise AppError(
                "Discount not found",
                code="discount_not_found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

    async def get_effective_discount(
        self,
        *,
        client_id: uuid.UUID | None = None,
        event_id: uuid.UUID | None = None,
    ) -> int:
        """Calculate the effective discount percent for a client/event.

        Returns the maximum applicable discount from:
        1. Global active discounts (no client/event filter)
        2. Event-specific active discounts
        3. Client-specific active discounts
        """
        now = datetime.now(UTC)
        stmt = select(Discount).where(
            Discount.is_active.is_(True),
            Discount.deleted_at.is_(None),
        )
        discounts = (await self._session.execute(stmt)).scalars().all()

        best = 0
        for d in discounts:
            if d.valid_from is not None and d.valid_from > now:
                continue
            if d.valid_until is not None and d.valid_until < now:
                continue
            if d.discount_type == DiscountType.GLOBAL:
                best = max(best, d.percent)
            elif d.discount_type == DiscountType.EVENT and d.event_id == event_id:
                best = max(best, d.percent)
            elif d.discount_type == DiscountType.CLIENT and d.client_id == client_id:
                best = max(best, d.percent)

        if client_id is not None:
            client = await self._session.get(Client, client_id)
            if client is not None:
                best = max(best, client.discount_percent)

        return best
