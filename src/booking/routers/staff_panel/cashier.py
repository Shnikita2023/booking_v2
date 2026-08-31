"""Staff cashier endpoints: sell, refund, cancel (S-5)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from booking.core.deps import SessionDep, require_role
from booking.core.dto import OrderItem, Principal
from booking.integrations.messaging.service import EmailService
from booking.integrations.messaging.stub import StubMailer
from booking.integrations.payments.mock import MockUniPaymentGateway
from booking.integrations.payments.service import PaymentService
from booking.models.users import RoleCode
from booking.repositories.orders import OrderRepository
from booking.schemas.order import OrderCreateRequest, OrderListResponse, OrderRead
from booking.schemas.payment import PaymentRead
from booking.services.order_service import OrderService

AdminManager = Annotated[Principal, Depends(require_role(RoleCode.ADMIN, RoleCode.MANAGER))]

router = APIRouter(prefix="/api/v1/staff/orders", tags=["staff-cashier"])


def _get_payment_service(session: SessionDep) -> PaymentService:
    return PaymentService(
        session,
        gateway=MockUniPaymentGateway(),
        email_service=EmailService(StubMailer(session)),
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create and pay order (cashier)",
    description="Staff creates a reservation and immediately pays it (cash/invoice).",
    response_model=OrderRead,
)
async def cashier_sell(
    body: OrderCreateRequest,
    session: SessionDep,
    _principal: AdminManager,
) -> OrderRead:
    order_svc = OrderService(session)
    order = await order_svc.reserve(
        client_id=uuid.uuid4(),  # anonymous/overridden by staff
        event_id=body.event_id,
        items=[
            OrderItem(ticket_type_id=item.ticket_type_id, quantity=item.quantity)
            for item in body.items
        ],
        actor=_principal,
    )
    pay_svc = _get_payment_service(session)
    await pay_svc.confirm_cash(
        order_id=order.id, client_id=order.client_id, actor=_principal
    )
    return OrderRead.from_order(order)


@router.post(
    "/{order_id}/refund",
    status_code=status.HTTP_200_OK,
    summary="Refund an order (cashier)",
    description="Staff refunds a PAID order.",
    response_model=PaymentRead,
)
async def staff_refund(
    order_id: uuid.UUID,
    session: SessionDep,
    _principal: AdminManager,
) -> PaymentRead:
    svc = _get_payment_service(session)
    payment = await svc.staff_refund(order_id=order_id, actor=_principal)
    return PaymentRead.from_payment(payment)


@router.post(
    "/{order_id}/cancel",
    status_code=status.HTTP_200_OK,
    summary="Cancel an order (cashier)",
    description="Staff cancels a RESERVED order and releases quota.",
    response_model=OrderRead,
)
async def staff_cancel(
    order_id: uuid.UUID,
    session: SessionDep,
    _principal: AdminManager,
) -> OrderRead:
    order_svc = OrderService(session)
    order = await order_svc.cancel_staff(order_id=order_id, actor=_principal)
    return OrderRead.from_order(order)


@router.get(
    "",
    summary="List all orders (cashier)",
    description="Staff views all orders (paginated).",
    response_model=OrderListResponse,
)
async def staff_list_orders(
    session: SessionDep,
    _principal: AdminManager,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> OrderListResponse:
    repo = OrderRepository(session)
    orders = await repo.list(limit=limit, offset=offset)
    return OrderListResponse(
        items=[OrderRead.from_order(o) for o in orders], total=len(orders)
    )
