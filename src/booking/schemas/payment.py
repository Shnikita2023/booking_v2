"""Payment schemas."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from booking.models.orders import Payment


class PaymentRead(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    status: str
    amount: Decimal
    external_id: str | None = None
    method: str
    currency: str
    gateway: str
    paid_at: datetime | None = None
    created_at: datetime

    @classmethod
    def from_payment(cls, payment: Payment) -> "PaymentRead":
        return cls(
            id=payment.id,
            order_id=payment.order_id,
            status=payment.status.value,
            amount=payment.amount,
            external_id=payment.external_id,
            method=payment.method,
            currency=payment.currency,
            gateway=payment.gateway,
            paid_at=payment.paid_at,
            created_at=payment.created_at,
        )


class PaymentIntentResponse(BaseModel):
    payment_id: uuid.UUID
    external_id: str
    redirect_url: str


class WebhookRequest(BaseModel):
    event_type: str
    external_id: str
    idempotency_key: str = ""
