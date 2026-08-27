import uuid

from fastapi import APIRouter, Query

from booking.core.deps import ClientPrincipal, SessionDep
from booking.core.dto import OrderItem
from booking.schemas.order import (
    OrderCreateRequest,
    OrderListResponse,
    OrderRead,
)
from booking.services.order_service import OrderService

router = APIRouter(prefix="/api/v1/orders", tags=["client-orders"])


@router.post("", status_code=201)
async def create_order(
    body: OrderCreateRequest,
    principal: ClientPrincipal,
    session: SessionDep,
) -> OrderRead:
    order = await OrderService(session).reserve(
        client_id=principal.user_id,
        event_id=body.event_id,
        items=[
            OrderItem(ticket_type_id=item.ticket_type_id, quantity=item.quantity)
            for item in body.items
        ],
    )
    return OrderRead.from_order(order)


@router.post("/{order_id}/pay", status_code=200)
async def pay_order(
    order_id: uuid.UUID,
    principal: ClientPrincipal,
    session: SessionDep,
) -> OrderRead:
    order = await OrderService(session).confirm_payment(
        order_id=order_id, client_id=principal.user_id
    )
    return OrderRead.from_order(order)


@router.post("/{order_id}/cancel", status_code=200)
async def cancel_order(
    order_id: uuid.UUID,
    principal: ClientPrincipal,
    session: SessionDep,
) -> OrderRead:
    order = await OrderService(session).cancel(
        order_id=order_id, client_id=principal.user_id
    )
    return OrderRead.from_order(order)


@router.get("")
async def list_orders(
    principal: ClientPrincipal,
    session: SessionDep,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> OrderListResponse:
    orders, total = await OrderService(session).list_for_client(
        principal.user_id, limit=limit, offset=offset
    )
    return OrderListResponse(
        items=[OrderRead.from_order(order) for order in orders], total=total
    )
