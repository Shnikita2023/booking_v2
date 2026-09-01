import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from booking.models.orders import Order, OrderStatus, Ticket
from booking.repositories.base import BaseRepository


class OrderRepository(BaseRepository[Order]):
    model = Order

    async def get_with_tickets(self, order_id: uuid.UUID) -> Order | None:
        stmt = (
            select(Order)
            .where(Order.id == order_id, Order.deleted_at.is_(None))
            .options(selectinload(Order.tickets))
        )
        result = await self._session.execute(stmt)
        order = result.scalar_one_or_none()
        if order is not None:
            await self._session.refresh(order, ["tickets"])
        return order

    async def get_owned(
        self, order_id: uuid.UUID, client_id: uuid.UUID, *, lock: bool = False
    ) -> Order | None:
        stmt = (
            select(Order)
            .where(
                Order.id == order_id,
                Order.client_id == client_id,
                Order.deleted_at.is_(None),
            )
            .options(selectinload(Order.tickets))
        )
        if lock:
            stmt = stmt.with_for_update()
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_client(
        self, client_id: uuid.UUID, *, limit: int = 50, offset: int = 0
    ) -> tuple[Sequence[Order], int]:
        condition = (Order.client_id == client_id) & Order.deleted_at.is_(None)
        stmt = (
            select(Order)
            .where(condition)
            .options(selectinload(Order.tickets))
            .order_by(Order.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        count_stmt = select(func.count()).select_from(Order).where(condition)
        orders = (await self._session.execute(stmt)).scalars().all()
        total = (await self._session.execute(count_stmt)).scalar_one()
        return orders, total

    async def list_expired(self, now: object) -> Sequence[Order]:
        stmt = (
            select(Order)
            .where(
                Order.status == OrderStatus.RESERVED,
                Order.reserved_until.is_not(None),
                Order.reserved_until < now,
                Order.deleted_at.is_(None),
            )
            .options(selectinload(Order.tickets))
            .with_for_update(skip_locked=True)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()


class TicketRepository(BaseRepository[Ticket]):
    model = Ticket

    async def list_for_order(self, order_id: uuid.UUID) -> Sequence[Ticket]:
        stmt = select(Ticket).where(
            Ticket.order_id == order_id, Ticket.deleted_at.is_(None)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()
