import uuid

from fastapi import APIRouter, Query

from booking.core.deps import ClientPrincipal, SessionDep
from booking.models.orders import Order
from booking.schemas.order import (
    OrderCreateRequest,
    OrderListResponse,
    OrderRead,
    TicketRead,
)
from booking.services.order_service import OrderItem, OrderService

router = APIRouter(prefix="/api/v1/orders", tags=["client-orders"])


def _to_read(order: Order) -> OrderRead:
    return OrderRead(
        id=order.id,
        event_id=order.event_id,
        status=order.status.value,
        total_amount=order.total_amount,
        reserved_until=order.reserved_until,
        created_at=order.created_at,
        tickets=[
            TicketRead(
                id=ticket.id,
                ticket_type_id=ticket.ticket_type_id,
                price=ticket.price,
                status=ticket.status.value,
            )
            for ticket in order.tickets
        ],
    )


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
    return _to_read(order)


@router.post("/{order_id}/pay", status_code=200)
async def pay_order(
    order_id: uuid.UUID,
    principal: ClientPrincipal,
    session: SessionDep,
) -> OrderRead:
    order = await OrderService(session).confirm_payment(
        order_id=order_id, client_id=principal.user_id
    )
    return _to_read(order)


@router.post("/{order_id}/cancel", status_code=200)
async def cancel_order(
    order_id: uuid.UUID,
    principal: ClientPrincipal,
    session: SessionDep,
) -> OrderRead:
    order = await OrderService(session).cancel(
        order_id=order_id, client_id=principal.user_id
    )
    return _to_read(order)


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
        items=[_to_read(order) for order in orders], total=total
    )
