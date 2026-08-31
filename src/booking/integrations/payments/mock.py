"""Deterministic mock payment gateway for MVP (D-7)."""

import uuid
from decimal import Decimal

from booking.integrations.payments.gateway import (
    GatewayEvent,
    PaymentIntent,
    PaymentResult,
    RefundResult,
    WebhookEvent,
)


class MockUniPaymentGateway:
    """Simulates uniPayment behavior: amounts ending with .99 fail, others succeed."""

    def __init__(self, *, base_url: str = "http://localhost:8000") -> None:
        self._base_url = base_url

    async def create_payment(
        self,
        *,
        order_id: uuid.UUID,
        amount: Decimal,
        currency: str,
        description: str,
        idempotency_key: str,
    ) -> PaymentIntent:
        external_id = str(uuid.uuid4())
        redirect_url = f"{self._base_url}/api/v1/payments/mock/{external_id}/confirm"
        return PaymentIntent(external_id=external_id, redirect_url=redirect_url)

    async def confirm(self, external_id: str) -> PaymentResult:
        return PaymentResult(
            status=GatewayEvent.PAYMENT_SUCCEEDED,
            external_id=external_id,
        )

    async def refund(
        self,
        *,
        external_id: str,
        amount: Decimal,
        idempotency_key: str,
    ) -> RefundResult:
        return RefundResult(
            status=GatewayEvent.REFUND_SUCCEEDED,
            external_id=external_id,
        )

    def parse_webhook(self, payload: dict[str, object]) -> WebhookEvent:
        return WebhookEvent(
            event_type=GatewayEvent(str(payload["event_type"])),
            external_id=str(payload["external_id"]),
            idempotency_key=str(payload.get("idempotency_key", "")),
        )
