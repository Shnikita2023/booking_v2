"""Payment gateway abstraction for external payment providers (D-7)."""

import uuid
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Protocol


class GatewayEvent(StrEnum):
    PAYMENT_SUCCEEDED = "payment.succeeded"
    PAYMENT_FAILED = "payment.failed"
    REFUND_SUCCEEDED = "refund.succeeded"


@dataclass(slots=True)
class PaymentIntent:
    external_id: str
    redirect_url: str


@dataclass(slots=True)
class PaymentResult:
    status: GatewayEvent
    external_id: str


@dataclass(slots=True)
class RefundResult:
    status: GatewayEvent
    external_id: str


@dataclass(slots=True)
class WebhookEvent:
    event_type: GatewayEvent
    external_id: str
    idempotency_key: str


class PaymentGateway(Protocol):
    async def create_payment(
        self,
        *,
        order_id: uuid.UUID,
        amount: Decimal,
        currency: str,
        description: str,
        idempotency_key: str,
    ) -> PaymentIntent: ...

    async def confirm(self, external_id: str) -> PaymentResult: ...

    async def refund(
        self,
        *,
        external_id: str,
        amount: Decimal,
        idempotency_key: str,
    ) -> RefundResult: ...

    def parse_webhook(self, payload: dict[str, object]) -> WebhookEvent: ...
