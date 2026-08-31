"""Client payment endpoints: create intent, refund (D-7)."""

import uuid

from fastapi import APIRouter, status

from booking.core.deps import ClientPrincipal, SessionDep
from booking.messaging.service import EmailService
from booking.messaging.stub import StubMailer
from booking.payments.mock import MockUniPaymentGateway
from booking.payments.service import PaymentService
from booking.schemas.payment import PaymentIntentResponse, PaymentRead

router = APIRouter(prefix="/api/v1/orders", tags=["client-payments"])


def _get_service(session: SessionDep) -> PaymentService:
    return PaymentService(
        session,
        gateway=MockUniPaymentGateway(),
        email_service=EmailService(StubMailer(session)),
    )


@router.post(
    "/{order_id}/pay",
    status_code=status.HTTP_201_CREATED,
    summary="Create payment intent",
    description="Create a payment intent for a RESERVED order. Returns a redirect URL "
    "to simulate the payment provider flow.",
    response_model=PaymentIntentResponse,
)
async def create_payment_intent(
    order_id: uuid.UUID,
    principal: ClientPrincipal,
    session: SessionDep,
) -> PaymentIntentResponse:
    svc = _get_service(session)
    payment = await svc.create_intent(
        order_id=order_id, client_id=principal.user_id, actor=principal
    )
    external_id = payment.external_id or ""
    return PaymentIntentResponse(
        payment_id=payment.id,
        external_id=external_id,
        redirect_url=f"/api/v1/payments/mock/{external_id}/confirm",
    )


@router.post(
    "/{order_id}/refund",
    status_code=status.HTTP_200_OK,
    summary="Refund a paid order",
    description="Refund a PAID order. Tickets are cancelled and quota released.",
    response_model=PaymentRead,
)
async def refund_order(
    order_id: uuid.UUID,
    principal: ClientPrincipal,
    session: SessionDep,
) -> PaymentRead:
    svc = _get_service(session)
    payment = await svc.refund_order(
        order_id=order_id, client_id=principal.user_id, actor=principal
    )
    return PaymentRead.from_payment(payment)
