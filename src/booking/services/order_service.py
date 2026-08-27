import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from booking.core.config import get_settings
from booking.core.errors import AppError
from booking.models.events import TicketType
from booking.models.orders import (
    Order,
    OrderStatus,
    Payment,
    PaymentStatus,
    Ticket,
    TicketStatus,
)
from booking.repositories.event import EventRepository, TicketTypeRepository
from booking.repositories.orders import (
    OrderRepository,
    PaymentRepository,
    TicketRepository,
)


@dataclass(slots=True)
class OrderItem:
    ticket_type_id: uuid.UUID
    quantity: int


class OrderService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._orders = OrderRepository(session)
        self._tickets = TicketRepository(session)
        self._payments = PaymentRepository(session)
        self._events = EventRepository(session)
        self._ticket_types = TicketTypeRepository(session)

    async def reserve(
        self, *, client_id: uuid.UUID, event_id: uuid.UUID, items: list[OrderItem]
    ) -> Order:
        if not items:
            raise AppError("Empty order", code="empty_order", status_code=400)
        event = await self._events.get_on_sale(event_id)
        if event is None:
            raise AppError("Event not found", code="event_not_found", status_code=404)
        if event.sale_paused:
            raise AppError("Sales paused", code="sales_paused", status_code=409)

        total = Decimal(0)
        locked: list[TicketType] = []
        for item in items:
            ticket_type = await self._ticket_types.lock(item.ticket_type_id)
            if ticket_type is None or ticket_type.deleted_at is not None:
                raise AppError(
                    "Ticket type not found", code="ticket_type_not_found", status_code=404
                )
            if ticket_type.sold + item.quantity > ticket_type.quota:
                raise AppError(
                    "Not enough tickets", code="sold_out", status_code=409
                )
            ticket_type.sold += item.quantity
            total += ticket_type.price * item.quantity
            locked.append(ticket_type)

        ttl = timedelta(minutes=get_settings().reservation_ttl_min)
        order = await self._orders.create(
            client_id=client_id,
            event_id=event_id,
            status=OrderStatus.RESERVED,
            total_amount=total,
            reserved_until=datetime.now(UTC) + ttl,
        )
        for item in items:
            ticket_type = next(
                t for t in locked if t.id == item.ticket_type_id
            )
            for _ in range(item.quantity):
                self._session.add(
                    Ticket(
                        order_id=order.id,
                        ticket_type_id=item.ticket_type_id,
                        price=ticket_type.price,
                        status=TicketStatus.ACTIVE,
                    )
                )
        await self._payments.create(
            order_id=order.id, status=PaymentStatus.PENDING, amount=total
        )
        await self._session.commit()
        loaded = await self._orders.get_with_tickets(order.id)
        assert loaded is not None
        return loaded

    async def confirm_payment(
        self, *, order_id: uuid.UUID, client_id: uuid.UUID
    ) -> Order:
        order = await self._orders.get_owned(order_id, client_id)
        if order is None:
            raise AppError("Order not found", code="order_not_found", status_code=404)
        if order.status != OrderStatus.RESERVED:
            raise AppError(
                "Order is not in reserved state", code="invalid_order_state", status_code=409
            )
        order.status = OrderStatus.PAID
        order.reserved_until = None
        await self._set_payment_status(order.id, PaymentStatus.SUCCEEDED)
        await self._session.commit()
        loaded = await self._orders.get_with_tickets(order.id)
        assert loaded is not None
        return loaded

    async def cancel(self, *, order_id: uuid.UUID, client_id: uuid.UUID) -> Order:
        order = await self._orders.get_owned(order_id, client_id)
        if order is None:
            raise AppError("Order not found", code="order_not_found", status_code=404)
        if order.status == OrderStatus.PAID:
            raise AppError(
                "Paid order cannot be cancelled here", code="paid_order_cannot_cancel",
                status_code=409,
            )
        if order.status == OrderStatus.CANCELLED:
            loaded = await self._orders.get_with_tickets(order.id)
            assert loaded is not None
            return loaded
        await self._release_quota(order)
        order.status = OrderStatus.CANCELLED
        for ticket in order.tickets:
            ticket.status = TicketStatus.CANCELLED
        await self._set_payment_status(order.id, PaymentStatus.FAILED)
        await self._session.commit()
        loaded = await self._orders.get_with_tickets(order.id)
        assert loaded is not None
        return loaded

    async def list_for_client(
        self, client_id: uuid.UUID, *, limit: int = 50, offset: int = 0
    ) -> tuple[list[Order], int]:
        orders, total = await self._orders.list_for_client(
            client_id, limit=limit, offset=offset
        )
        return list(orders), total

    async def get_client_order(
        self, *, order_id: uuid.UUID, client_id: uuid.UUID
    ) -> Order:
        order = await self._orders.get_owned(order_id, client_id)
        if order is None:
            raise AppError("Order not found", code="order_not_found", status_code=404)
        return order

    async def cleanup_expired(self) -> int:
        now = datetime.now(UTC)
        expired = await self._orders.list_expired(now)
        count = 0
        for order in expired:
            await self._release_quota(order)
            order.status = OrderStatus.CANCELLED
            for ticket in order.tickets:
                ticket.status = TicketStatus.CANCELLED
            await self._set_payment_status(order.id, PaymentStatus.FAILED)
            count += 1
        if count:
            await self._session.commit()
        return count

    async def _release_quota(self, order: Order) -> None:
        by_type: dict[uuid.UUID, int] = {}
        for ticket in order.tickets:
            by_type[ticket.ticket_type_id] = by_type.get(ticket.ticket_type_id, 0) + 1
        for ticket_type_id, qty in by_type.items():
            ticket_type = await self._ticket_types.lock(ticket_type_id)
            if ticket_type is not None:
                ticket_type.sold = max(0, ticket_type.sold - qty)

    async def _set_payment_status(
        self, order_id: uuid.UUID, status: PaymentStatus
    ) -> None:
        stmt = await self._session.execute(
            select(Payment).where(Payment.order_id == order_id)
        )
        payment = stmt.scalar_one_or_none()
        if payment is not None:
            payment.status = status
