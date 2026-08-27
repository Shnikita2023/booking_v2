import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


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


class OrderRead(BaseModel):
    id: uuid.UUID
    event_id: uuid.UUID
    status: str
    total_amount: Decimal
    reserved_until: datetime | None
    created_at: datetime
    tickets: list[TicketRead]


class OrderListResponse(BaseModel):
    items: list[OrderRead]
    total: int
