"""Email sending service (D-8)."""

from booking.integrations.messaging.mailer import Mailer


class EmailService:
    def __init__(self, mailer: Mailer) -> None:
        self._mailer = mailer

    async def order_confirmation(
        self, *, to: str, order_id: str, event_title: str, total: str
    ) -> None:
        await self._mailer.send(
            to=to,
            subject=f"Order {order_id} confirmed",
            body=f"Your order {order_id} for {event_title} is confirmed. Total: {total}.",
            template="order_confirmation",
        )

    async def payment_confirmation(
        self, *, to: str, order_id: str, amount: str
    ) -> None:
        await self._mailer.send(
            to=to,
            subject=f"Payment received for order {order_id}",
            body=f"Payment of {amount} received for order {order_id}.",
            template="payment_confirmation",
        )

    async def order_cancelled(
        self, *, to: str, order_id: str, reason: str
    ) -> None:
        await self._mailer.send(
            to=to,
            subject=f"Order {order_id} cancelled",
            body=f"Order {order_id} has been cancelled. Reason: {reason}.",
            template="order_cancelled",
        )

    async def refund_processed(
        self, *, to: str, order_id: str, amount: str
    ) -> None:
        await self._mailer.send(
            to=to,
            subject=f"Refund for order {order_id}",
            body=f"Refund of {amount} has been processed for order {order_id}.",
            template="refund_processed",
        )

    async def eticket(
        self,
        *,
        to: str,
        order_id: str,
        event_title: str,
        tickets: list[str],
    ) -> None:
        ticket_list = "\n".join(f"  - {t}" for t in tickets)
        await self._mailer.send(
            to=to,
            subject=f"E-tickets for order {order_id}",
            body=f"Your e-tickets for {event_title}:\n{ticket_list}",
            template="eticket",
        )
