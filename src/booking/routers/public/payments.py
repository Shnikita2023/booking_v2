"""Public payment endpoints: webhook and mock confirm (D-7)."""

import hashlib
import hmac

from fastapi import APIRouter, Header, HTTPException, Request, status

from booking.core.config import get_settings
from booking.core.deps import PaymentServiceDep
from booking.schemas.payment import WebhookRequest

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


def _verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify HMAC-SHA256 signature of the webhook payload."""
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    summary="Payment webhook",
    description="Receive a payment status update from the payment provider. "
    "Requires X-Webhook-Signature header with HMAC-SHA256 signature.",
)
async def payment_webhook(
    request: Request,
    body: WebhookRequest,
    service: PaymentServiceDep,
    x_webhook_signature: str = Header(alias="X-Webhook-Signature"),
) -> dict[str, str]:
    raw_body = await request.body()
    settings = get_settings()
    if not _verify_webhook_signature(raw_body, x_webhook_signature, settings.webhook_secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )
    await service.handle_webhook(body.model_dump())
    return {"status": "ok"}


@router.post(
    "/mock/{external_id}/confirm",
    status_code=status.HTTP_200_OK,
    summary="Mock payment confirm",
    description="Simulate a successful payment confirmation (mock mode only).",
)
async def mock_confirm(external_id: str, service: PaymentServiceDep) -> dict[str, str]:
    await service.handle_webhook(
        {"event_type": "payment.succeeded", "external_id": external_id}
    )
    return {"status": "ok"}
