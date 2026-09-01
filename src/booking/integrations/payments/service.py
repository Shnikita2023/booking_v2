"""Payment lifecycle: intent, webhook confirm, refund, cashier (D-7, S-5)."""

import uuid
from collections import defaultdict
from datetime import UTC, datetime

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from booking.core.dto import Principal
from booking.core.errors import AppError
from booking.integrations.messaging.service import EmailService
from booking.integrations.payments.gateway import GatewayEvent, PaymentGateway
from booking.models.audit import AuditAction
from booking.models.events import Event
from booking.models.orders import (
    Order,
    OrderStatus,
    Payment,
    PaymentStatus,
    TicketStatus,
)
from booking.repositories.clients import ClientRepository
from booking.repositories.event import TicketTypeRepository
from booking.repositories.orders import OrderRepository, TicketRepository
from booking.repositories.payments import PaymentRepository
from booking.services.audit_service import AuditService


class PaymentService:
    def __init__(
        self,
        session: AsyncSession,
        gateway: PaymentGateway,
        email_service: EmailService,
    ) -> None:
        self._session = session
        self._gateway = gateway
        self._email = email_service
        self._orders = OrderRepository(session)
        self._payments = PaymentRepository(session)
        self._tickets = TicketRepository(session)
        self._clients = ClientRepository(session)
        self._audit = AuditService(session)

    async def create_intent(
        self,
        *,
        order_id: uuid.UUID,
        client_id: uuid.UUID,
        actor: Principal | None = None,
    ) -> Payment:
        """Create a payment intent (PENDING) and return redirect URL."""
        order = await self._orders.get_owned(order_id, client_id, lock=True)
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
        payment = await self._payments.get_by_order(order_id)
        if payment is None:
            raise AppError(
                "Payment not found", code="payment_not_found", status_code=status.HTTP_404_NOT_FOUND
            )
        if payment.status != PaymentStatus.PENDING:
            raise AppError(
                "Payment already processed",
                code="payment_already_processed",
                status_code=status.HTTP_409_CONFLICT,
            )
        idempotency_key = f"pay_{order_id}_{uuid.uuid4().hex[:12]}"
        payment.idempotency_key = idempotency_key
        intent = await self._gateway.create_payment(
            order_id=order_id,
            amount=order.total_amount,
            currency="RUB",
            description=f"Order {order_id}",
            idempotency_key=idempotency_key,
        )
        payment.external_id = intent.external_id
        await self._audit.record(
            action=AuditAction.PAYMENT_CREATED,
            entity_type="payment",
            entity_id=payment.id,
            actor=actor,
            payload={"order_id": str(order_id), "external_id": intent.external_id},
        )
        await self._session.commit()
        return payment

    async def handle_webhook(
        self, payload: dict[str, object], *, actor: Principal | None = None
    ) -> None:
        """Process a payment webhook event (idempotent)."""
        event = self._gateway.parse_webhook(payload)
        payment = await self._payments.get_by_external_id(event.external_id)
        if payment is None:
            raise AppError(
                "Payment not found", code="payment_not_found", status_code=status.HTTP_404_NOT_FOUND
            )
        already_succeeded = (
            payment.status == PaymentStatus.SUCCEEDED
            and event.event_type == GatewayEvent.PAYMENT_SUCCEEDED
        )
        if already_succeeded:
            return  # idempotent
        if event.event_type == GatewayEvent.PAYMENT_SUCCEEDED:
            payment.status = PaymentStatus.SUCCEEDED
            payment.paid_at = datetime.now(UTC)
            order = await self._orders.get_with_tickets(payment.order_id)
            if order is not None:
                order.status = OrderStatus.PAID
                order.reserved_until = None
                client = await self._clients.get(order.client_id)
                if client is not None:
                    await self._email.payment_confirmation(
                        to=client.email,
                        order_id=str(order.id),
                        amount=str(payment.amount),
                    )
                    ticket_ids = [str(t.id) for t in order.tickets]
                    if ticket_ids:
                        event_model = await self._session.get(Event, order.event_id)
                        await self._email.eticket(
                            to=client.email,
                            order_id=str(order.id),
                            event_title=event_model.title if event_model else "Event",
                            tickets=ticket_ids,
                        )
            await self._audit.record(
                action=AuditAction.PAYMENT_SUCCEEDED,
                entity_type="payment",
                entity_id=payment.id,
                actor=actor,
                payload={"order_id": str(payment.order_id)},
            )
            await self._session.commit()
        elif event.event_type == GatewayEvent.PAYMENT_FAILED:
            payment.status = PaymentStatus.FAILED
            await self._audit.record(
                action=AuditAction.PAYMENT_FAILED,
                entity_type="payment",
                entity_id=payment.id,
                actor=actor,
                payload={"order_id": str(payment.order_id)},
            )
            await self._session.commit()

    async def confirm_cash(
        self,
        *,
        order_id: uuid.UUID,
        client_id: uuid.UUID,
        actor: Principal | None = None,
    ) -> Payment:
        """Cashier: immediately confirm payment (no redirect)."""
        order = await self._orders.get_owned(order_id, client_id, lock=True)
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
        payment = await self._payments.get_by_order(order_id)
        if payment is None:
            raise AppError(
                "Payment not found", code="payment_not_found", status_code=status.HTTP_404_NOT_FOUND
            )
        payment.status = PaymentStatus.SUCCEEDED
        payment.paid_at = datetime.now(UTC)
        order.status = OrderStatus.PAID
        order.reserved_until = None
        await self._audit.record(
            action=AuditAction.CASHIER_SALE,
            entity_type="order",
            entity_id=order.id,
            actor=actor,
            payload={"method": "cash"},
        )
        await self._session.commit()
        client = await self._clients.get(order.client_id)
        if client is not None:
            await self._email.payment_confirmation(
                to=client.email,
                order_id=str(order.id),
                amount=str(payment.amount),
            )
        return payment

    async def _release_quota_for_order(self, order: Order) -> None:
        """Release ticket quota for an order."""
        by_type: dict[uuid.UUID, int] = defaultdict(int)
        for ticket in order.tickets:
            by_type[ticket.ticket_type_id] += 1
        tt_repo = TicketTypeRepository(self._session)
        for tt_id, qty in by_type.items():
            tt = await tt_repo.lock_skip_locked(tt_id)
            if tt is not None:
                tt.sold = max(0, tt.sold - qty)

    async def refund_order(
        self,
        *,
        order_id: uuid.UUID,
        client_id: uuid.UUID,
        actor: Principal | None = None,
    ) -> Payment:
        """Refund a PAID order, marking it REFUNDED."""
        order = await self._orders.get_owned(order_id, client_id, lock=True)
        if order is None:
            raise AppError(
                "Order not found", code="order_not_found", status_code=status.HTTP_404_NOT_FOUND
            )
        if order.status != OrderStatus.PAID:
            raise AppError(
                "Only paid orders can be refunded",
                code="invalid_order_state",
                status_code=status.HTTP_409_CONFLICT,
            )
        payment = await self._payments.get_by_order(order_id)
        if payment is None:
            raise AppError(
                "Payment not found", code="payment_not_found", status_code=status.HTTP_404_NOT_FOUND
            )
        idempotency_key = f"refund_{order_id}_{uuid.uuid4().hex[:12]}"
        result = await self._gateway.refund(
            external_id=payment.external_id or "",
            amount=order.total_amount,
            idempotency_key=idempotency_key,
        )
        if result.status == GatewayEvent.REFUND_SUCCEEDED:
            payment.status = PaymentStatus.REFUNDED
            order.status = OrderStatus.REFUNDED
            for ticket in order.tickets:
                ticket.status = TicketStatus.CANCELLED
            await self._release_quota_for_order(order)
            await self._audit.record(
                action=AuditAction.PAYMENT_REFUNDED,
                entity_type="payment",
                entity_id=payment.id,
                actor=actor,
                payload={"order_id": str(order_id)},
            )
            await self._session.commit()
            client = await self._clients.get(order.client_id)
            if client is not None:
                await self._email.refund_processed(
                    to=client.email,
                    order_id=str(order.id),
                    amount=str(order.total_amount),
                )
        return payment

    async def staff_refund(
        self,
        *,
        order_id: uuid.UUID,
        actor: Principal | None = None,
    ) -> Payment:
        """Staff cashier refund (no client_id scoping)."""
        order = await self._orders.get_with_tickets(order_id)
        if order is None:
            raise AppError(
                "Order not found", code="order_not_found", status_code=status.HTTP_404_NOT_FOUND
            )
        if order.status != OrderStatus.PAID:
            raise AppError(
                "Only paid orders can be refunded",
                code="invalid_order_state",
                status_code=status.HTTP_409_CONFLICT,
            )
        payment = await self._payments.get_by_order(order_id)
        if payment is None:
            raise AppError(
                "Payment not found", code="payment_not_found", status_code=status.HTTP_404_NOT_FOUND
            )
        idempotency_key = f"refund_{order_id}_{uuid.uuid4().hex[:12]}"
        result = await self._gateway.refund(
            external_id=payment.external_id or "",
            amount=order.total_amount,
            idempotency_key=idempotency_key,
        )
        if result.status == GatewayEvent.REFUND_SUCCEEDED:
            payment.status = PaymentStatus.REFUNDED
            order.status = OrderStatus.REFUNDED
            for ticket in order.tickets:
                ticket.status = TicketStatus.CANCELLED
            await self._release_quota_for_order(order)
            await self._audit.record(
                action=AuditAction.PAYMENT_REFUNDED,
                entity_type="payment",
                entity_id=payment.id,
                actor=actor,
                payload={"order_id": str(order_id)},
            )
            await self._session.commit()
            client = await self._clients.get(order.client_id)
            if client is not None:
                await self._email.refund_processed(
                    to=client.email,
                    order_id=str(order.id),
                    amount=str(order.total_amount),
                )
        return payment
