"""Order lifecycle: reservation, payment, cancellation and TTL cleanup."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from booking.core.config import Settings, get_settings
from booking.core.dto import OrderItem
from booking.core.errors import AppError
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


class OrderService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings | None = None,
    ) -> None:
        self._session = session
        self._settings = settings or get_settings()
        self._orders = OrderRepository(session)
        self._tickets = TicketRepository(session)
        self._payments = PaymentRepository(session)
        self._events = EventRepository(session)
        self._ticket_types = TicketTypeRepository(session)

    async def reserve(
        self, *, client_id: uuid.UUID, event_id: uuid.UUID, items: list[OrderItem]
    ) -> Order:
        """Create a RESERVED order, atomically reserving quota per ticket type."""
        if not items:
            raise AppError(
                "Empty order", code="empty_order", status_code=status.HTTP_400_BAD_REQUEST
            )
        event = await self._events.get_on_sale(event_id)
        if event is None:
            raise AppError(
                "Event not found", code="event_not_found", status_code=status.HTTP_404_NOT_FOUND
            )
        if event.sale_paused:
            raise AppError(
                "Sales paused", code="sales_paused", status_code=status.HTTP_409_CONFLICT
            )

        total = Decimal(0)
        ttl = timedelta(minutes=self._settings.reservation_ttl_min)
        order = await self._orders.create(
            client_id=client_id,
            event_id=event_id,
            status=OrderStatus.RESERVED,
            total_amount=total,
            reserved_until=datetime.now(UTC) + ttl,
        )
        await self._session.refresh(order, ["tickets"])
        for item in items:
            ticket_type = await self._ticket_types.lock(item.ticket_type_id)
            if ticket_type is None or ticket_type.deleted_at is not None:
                raise AppError(
                    "Ticket type not found",
                    code="ticket_type_not_found",
                    status_code=status.HTTP_404_NOT_FOUND,
                )
            if ticket_type.sold + item.quantity > ticket_type.quota:
                raise AppError(
                    "Not enough tickets", code="sold_out", status_code=status.HTTP_409_CONFLICT
                )
            ticket_type.sold += item.quantity
            total += ticket_type.price * item.quantity
            for _ in range(item.quantity):
                order.tickets.append(
                    Ticket(
                        ticket_type_id=item.ticket_type_id,
                        price=ticket_type.price,
                        status=TicketStatus.ACTIVE,
                    )
                )
        order.total_amount = total
        await self._payments.create(order_id=order.id, status=PaymentStatus.PENDING, amount=total)
        await self._session.commit()
        return order

    async def confirm_payment(self, *, order_id: uuid.UUID, client_id: uuid.UUID) -> Order:
        """Transition a RESERVED order to PAID and mark its payment succeeded."""
        order = await self._orders.get_owned(order_id, client_id)
        if order is None:
            raise AppError(
                "Order not found", code="order_not_found", status_code=status.HTTP_404_NOT_FOUND
            )
        if order.status != OrderStatus.RESERVED:
            raise AppError(
                "Order is not in reserved state",
                code="invalid_order_state",
                status_code=status.HTTP_409_CONFLICT,
            )
        order.status = OrderStatus.PAID
        order.reserved_until = None
        await self._set_payment_status(order.id, PaymentStatus.SUCCEEDED)
        await self._session.commit()
        return order

    async def cancel(self, *, order_id: uuid.UUID, client_id: uuid.UUID) -> Order:
        """Cancel an order under row lock, releasing quota; idempotent if already cancelled."""
        order = await self._orders.get_owned(order_id, client_id, lock=True)
        if order is None:
            raise AppError(
                "Order not found", code="order_not_found", status_code=status.HTTP_404_NOT_FOUND
            )
        if order.status == OrderStatus.PAID:
            raise AppError(
                "Paid order cannot be cancelled here",
                code="paid_order_cannot_cancel",
                status_code=status.HTTP_409_CONFLICT,
            )
        if order.status == OrderStatus.CANCELLED:
            return order
        await self._release_quota(order)
        order.status = OrderStatus.CANCELLED
        for ticket in order.tickets:
            ticket.status = TicketStatus.CANCELLED
        await self._set_payment_status(order.id, PaymentStatus.FAILED)
        await self._session.commit()
        return order

    async def list_for_client(
        self, client_id: uuid.UUID, *, limit: int = 50, offset: int = 0
    ) -> tuple[list[Order], int]:
        """Return a paginated list of a client's orders with their tickets."""
        orders, total = await self._orders.list_for_client(client_id, limit=limit, offset=offset)
        return list(orders), total

    async def get_client_order(self, *, order_id: uuid.UUID, client_id: uuid.UUID) -> Order:
        """Return a single client-owned order, or raise if not found."""
        order = await self._orders.get_owned(order_id, client_id)
        if order is None:
            raise AppError(
                "Order not found", code="order_not_found", status_code=status.HTTP_404_NOT_FOUND
            )
        return order

    async def cleanup_expired(self) -> int:
        """Cancel expired RESERVED orders, releasing quota exactly once per order.

        Expired rows are locked with SKIP LOCKED in ``list_expired``, so exactly
        one transaction (across replicas) handles each order; a status recheck
        makes the release idempotent against a concurrent cancel.
        """
        now = datetime.now(UTC)
        expired = await self._orders.list_expired(now)
        count = 0
        for order in expired:
            if order.status != OrderStatus.RESERVED:
                continue
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
        """Return reserved ticket quantities to their ticket types (never below 0)."""
        by_type: dict[uuid.UUID, int] = {}
        for ticket in order.tickets:
            by_type[ticket.ticket_type_id] = by_type.get(ticket.ticket_type_id, 0) + 1
        for ticket_type_id, qty in by_type.items():
            ticket_type = await self._ticket_types.lock(ticket_type_id)
            if ticket_type is not None:
                ticket_type.sold = max(0, ticket_type.sold - qty)

    async def _set_payment_status(self, order_id: uuid.UUID, status: PaymentStatus) -> None:
        """Update the payment row linked to an order, if present."""
        stmt = await self._session.execute(select(Payment).where(Payment.order_id == order_id))
        payment = stmt.scalar_one_or_none()
        if payment is not None:
            payment.status = status
