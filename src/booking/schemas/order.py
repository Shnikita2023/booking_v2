import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from booking.models.orders import Order, Ticket


class OrderItemRequest(BaseModel):
    ticket_type_id: uuid.UUID
    quantity: int = Field(ge=1, le=20)


class OrderCreateRequest(BaseModel):
    event_id: uuid.UUID
    items: list[OrderItemRequest] = Field(min_length=1, max_length=50)


class TicketRead(BaseModel):
    id: uuid.UUID
    ticket_type_id: uuid.UUID
    price: Decimal
    status: str

    @classmethod
    def from_ticket(cls, ticket: Ticket) -> "TicketRead":
        return cls(
            id=ticket.id,
            ticket_type_id=ticket.ticket_type_id,
            price=ticket.price,
            status=ticket.status.value,
        )


class OrderRead(BaseModel):
    id: uuid.UUID
    event_id: uuid.UUID
    status: str
    total_amount: Decimal
    reserved_until: datetime | None
    created_at: datetime
    tickets: list[TicketRead]

    @classmethod
    def from_order(cls, order: Order) -> "OrderRead":
        return cls(
            id=order.id,
            event_id=order.event_id,
            status=order.status.value,
            total_amount=order.total_amount,
            reserved_until=order.reserved_until,
            created_at=order.created_at,
            tickets=[TicketRead.from_ticket(t) for t in order.tickets],
        )


class OrderListResponse(BaseModel):
    items: list[OrderRead]
    total: int
