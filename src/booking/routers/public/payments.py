"""Public payment endpoints: webhook and mock confirm (D-7)."""

from fastapi import APIRouter, status

from booking.core.deps import SessionDep
from booking.messaging.service import EmailService
from booking.messaging.stub import StubMailer
from booking.payments.mock import MockUniPaymentGateway
from booking.payments.service import PaymentService
from booking.schemas.payment import WebhookRequest

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


def _get_service(session: SessionDep) -> PaymentService:
    return PaymentService(
        session,
        gateway=MockUniPaymentGateway(),
        email_service=EmailService(StubMailer(session)),
    )


@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    summary="Payment webhook",
    description="Receive a payment status update from the payment provider.",
)
async def payment_webhook(body: WebhookRequest, session: SessionDep) -> dict[str, str]:
    svc = _get_service(session)
    await svc.handle_webhook(body.model_dump())
    return {"status": "ok"}


@router.post(
    "/mock/{external_id}/confirm",
    status_code=status.HTTP_200_OK,
    summary="Mock payment confirm",
    description="Simulate a successful payment confirmation (mock mode only).",
)
async def mock_confirm(external_id: str, session: SessionDep) -> dict[str, str]:
    svc = _get_service(session)
    await svc.handle_webhook(
        {"event_type": "payment.succeeded", "external_id": external_id}
    )
    return {"status": "ok"}
