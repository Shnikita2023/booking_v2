"""Staff cashier endpoints: sell, refund, cancel (S-5)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from booking.core.deps import OrderServiceDep, PaymentServiceDep, require_role
from booking.core.dto import OrderItem, Principal
from booking.models.users import RoleCode
from booking.schemas.order import OrderCreateRequest, OrderListResponse, OrderRead
from booking.schemas.payment import PaymentRead

AdminManager = Annotated[Principal, Depends(require_role(RoleCode.ADMIN, RoleCode.MANAGER))]

router = APIRouter(prefix="/api/v1/staff/orders", tags=["staff-cashier"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create and pay order (cashier)",
    description="Staff creates a reservation and immediately pays it (cash/invoice).",
    response_model=OrderRead,
)
async def cashier_sell(
    body: OrderCreateRequest,
    order_service: OrderServiceDep,
    payment_service: PaymentServiceDep,
    _principal: AdminManager,
) -> OrderRead:
    order = await order_service.reserve(
        client_id=None,  # anonymous cashier sale
        event_id=body.event_id,
        items=[
            OrderItem(ticket_type_id=item.ticket_type_id, quantity=item.quantity)
            for item in body.items
        ],
        actor=_principal,
    )
    await payment_service.confirm_cash(
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
    payment_service: PaymentServiceDep,
    _principal: AdminManager,
) -> PaymentRead:
    payment = await payment_service.staff_refund(order_id=order_id, actor=_principal)
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
    order_service: OrderServiceDep,
    _principal: AdminManager,
) -> OrderRead:
    order = await order_service.cancel_staff(order_id=order_id, actor=_principal)
    return OrderRead.from_order(order)


@router.get(
    "",
    summary="List all orders (cashier)",
    description="Staff views all orders (paginated).",
    response_model=OrderListResponse,
)
async def staff_list_orders(
    order_service: OrderServiceDep,
    _principal: AdminManager,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> OrderListResponse:
    orders = await order_service.list_all(limit=limit, offset=offset)
    return OrderListResponse(
        items=[OrderRead.from_order(o) for o in orders], total=len(orders)
    )
