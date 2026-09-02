"""Payment, cashier and refund flow tests (D-7, S-5)."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from booking.models.clients import Client
from booking.models.events import Event, EventStatus, TicketType
from booking.models.orders import (
    Order,
    OrderStatus,
    Payment,
    PaymentStatus,
    Ticket,
    TicketStatus,
)
from booking.models.users import RoleCode
from booking.repositories.clients import ClientRepository
from booking.services import security

FUTURE = datetime(2030, 5, 1, 18, 0, tzinfo=UTC)


def _headers(subject: str, role: str | None = None) -> dict[str, str]:
    extra = {"ut": "system_user"}
    if role is not None:
        extra["role"] = role
    token, _ = security.create_token("access", subject, extra_claims=extra)
    return {"Authorization": f"Bearer {token}"}


def _client_headers(subject: str) -> dict[str, str]:
    token, _ = security.create_token("access", subject, extra_claims={"ut": "client"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def event_with_tickets(web_session: AsyncSession) -> tuple[Event, TicketType]:
    event = Event(
        title="Concert",
        starts_at=FUTURE,
        status=EventStatus.ON_SALE,
        price=None,
        show_free_tickets=False,
        sale_paused=False,
        venue="Hall",
        age_rating="12+",
    )
    web_session.add(event)
    await web_session.flush()
    tt = TicketType(event_id=event.id, name="Std", price=Decimal("100.00"), quota=10, sold=0)
    web_session.add(tt)
    await web_session.commit()
    return event, tt


@pytest.fixture
async def buyer(web_session: AsyncSession) -> Client:
    client = await ClientRepository(web_session).create(
        email="buyer@example.com",
        full_name="Buyer",
        phone=None,
        password_hash=security.hash_password("pass123"),
        is_active=True,
        discount_percent=0,
    )
    await web_session.commit()
    return client


async def test_cashier_sell(
    client: AsyncClient,
    staff_user: dict[str, str],
    event_with_tickets: tuple[Event, TicketType],
    web_session: AsyncSession,
) -> None:
    event, tt = event_with_tickets
    headers = _headers(staff_user["id"], role=RoleCode.ADMIN.value)
    resp = await client.post(
        "/api/v1/staff/orders",
        headers=headers,
        json={
            "event_id": str(event.id),
            "items": [
                {
                    "ticket_type_id": str(tt.id),
                    "quantity": 2,
                }
            ],
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "paid"
    assert body["total_amount"] == "200.00"


async def test_staff_refund(
    client: AsyncClient,
    staff_user: dict[str, str],
    event_with_tickets: tuple[Event, TicketType],
    buyer: Client,
    web_session: AsyncSession,
) -> None:
    event, tt = event_with_tickets
    order = Order(
        client_id=buyer.id,
        event_id=event.id,
        status=OrderStatus.PAID,
        total_amount=Decimal("100.00"),
    )
    web_session.add(order)
    await web_session.flush()
    ticket = Ticket(
        order_id=order.id,
        ticket_type_id=tt.id,
        price=Decimal("100.00"),
        status=TicketStatus.ACTIVE,
    )
    web_session.add(ticket)
    payment = Payment(
        order_id=order.id,
        status=PaymentStatus.SUCCEEDED,
        amount=Decimal("100.00"),
        method="card",
        currency="RUB",
        gateway="mock",
        paid_at=datetime.now(UTC),
    )
    web_session.add(payment)
    await web_session.commit()

    headers = _headers(staff_user["id"], role=RoleCode.ADMIN.value)
    resp = await client.post(
        f"/api/v1/staff/orders/{order.id}/refund",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "refunded"


async def test_staff_cancel(
    client: AsyncClient,
    staff_user: dict[str, str],
    event_with_tickets: tuple[Event, TicketType],
    buyer: Client,
    web_session: AsyncSession,
) -> None:
    event, tt = event_with_tickets
    order = Order(
        client_id=buyer.id,
        event_id=event.id,
        status=OrderStatus.RESERVED,
        total_amount=Decimal("100.00"),
    )
    web_session.add(order)
    await web_session.flush()
    ticket = Ticket(
        order_id=order.id,
        ticket_type_id=tt.id,
        price=Decimal("100.00"),
        status=TicketStatus.ACTIVE,
    )
    web_session.add(ticket)
    payment = Payment(
        order_id=order.id,
        status=PaymentStatus.PENDING,
        amount=Decimal("100.00"),
    )
    web_session.add(payment)
    await web_session.commit()

    headers = _headers(staff_user["id"], role=RoleCode.ADMIN.value)
    resp = await client.post(
        f"/api/v1/staff/orders/{order.id}/cancel",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "cancelled"


async def test_staff_list_orders(
    client: AsyncClient,
    staff_user: dict[str, str],
    event_with_tickets: tuple[Event, TicketType],
    buyer: Client,
    web_session: AsyncSession,
) -> None:
    event, _tt = event_with_tickets
    order = Order(
        client_id=buyer.id,
        event_id=event.id,
        status=OrderStatus.PAID,
        total_amount=Decimal("100.00"),
    )
    web_session.add(order)
    await web_session.flush()
    payment = Payment(
        order_id=order.id,
        status=PaymentStatus.SUCCEEDED,
        amount=Decimal("100.00"),
    )
    web_session.add(payment)
    await web_session.commit()

    headers = _headers(staff_user["id"], role=RoleCode.ADMIN.value)
    resp = await client.get("/api/v1/staff/orders", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] >= 1


async def test_client_refund(
    client: AsyncClient,
    event_with_tickets: tuple[Event, TicketType],
    buyer: Client,
    web_session: AsyncSession,
) -> None:
    event, tt = event_with_tickets
    order = Order(
        client_id=buyer.id,
        event_id=event.id,
        status=OrderStatus.PAID,
        total_amount=Decimal("100.00"),
    )
    web_session.add(order)
    await web_session.flush()
    ticket = Ticket(
        order_id=order.id,
        ticket_type_id=tt.id,
        price=Decimal("100.00"),
        status=TicketStatus.ACTIVE,
    )
    web_session.add(ticket)
    payment = Payment(
        order_id=order.id,
        status=PaymentStatus.SUCCEEDED,
        amount=Decimal("100.00"),
        method="card",
        currency="RUB",
        gateway="mock",
        paid_at=datetime.now(UTC),
    )
    web_session.add(payment)
    await web_session.commit()

    headers = _client_headers(str(buyer.id))
    resp = await client.post(
        f"/api/v1/orders/{order.id}/refund",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "refunded"


async def test_discount_crud(
    client: AsyncClient,
    staff_user: dict[str, str],
) -> None:
    headers = _headers(staff_user["id"], role=RoleCode.ADMIN.value)

    created = await client.post(
        "/api/v1/admin/discounts",
        headers=headers,
        json={
            "name": "Summer Sale",
            "percent": 15,
            "discount_type": "global",
            "is_active": True,
        },
    )
    assert created.status_code == 201, created.text
    discount_id = created.json()["id"]
    assert created.json()["name"] == "Summer Sale"
    assert created.json()["percent"] == 15

    listed = await client.get("/api/v1/admin/discounts", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    got = await client.get(f"/api/v1/admin/discounts/{discount_id}", headers=headers)
    assert got.status_code == 200
    assert got.json()["name"] == "Summer Sale"

    updated = await client.put(
        f"/api/v1/admin/discounts/{discount_id}",
        headers=headers,
        json={"percent": 20},
    )
    assert updated.status_code == 200
    assert updated.json()["percent"] == 20

    deleted = await client.delete(f"/api/v1/admin/discounts/{discount_id}", headers=headers)
    assert deleted.status_code == 204


async def test_client_profile(
    client: AsyncClient,
    buyer: Client,
) -> None:
    headers = _client_headers(str(buyer.id))

    resp = await client.get("/api/v1/client/profile", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["email"] == "buyer@example.com"
    assert body["full_name"] == "Buyer"

    updated = await client.put(
        "/api/v1/client/profile",
        headers=headers,
        json={"full_name": "Updated Name"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["full_name"] == "Updated Name"
