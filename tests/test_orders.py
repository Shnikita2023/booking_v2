import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from booking.models.events import Event, EventStatus, TicketType
from booking.repositories.clients import ClientRepository
from booking.repositories.orders import OrderRepository
from booking.services import security
from booking.services.order_service import OrderItem, OrderService


@pytest_asyncio.fixture
async def client_user(web_session: AsyncSession) -> tuple[uuid.UUID, str]:
    repo = ClientRepository(web_session)
    user = await repo.create(
        email="buyer@example.com",
        password_hash=security.hash_password("buyerpass123"),
        discount_percent=0,
    )
    await web_session.commit()
    token, _ = security.create_token(
        "access", str(user.id), extra_claims={"ut": "client"}
    )
    return user.id, token


@pytest_asyncio.fixture
async def on_sale_event(web_session: AsyncSession) -> tuple[Event, TicketType]:
    event = Event(
        title="Show",
        starts_at=datetime.now(UTC) + timedelta(days=1),
        status=EventStatus.ON_SALE,
        price=None,
        show_free_tickets=True,
        sale_paused=False,
        venue="Hall",
        age_rating="6+",
    )
    web_session.add(event)
    await web_session.flush()
    ticket_type = TicketType(
        event_id=event.id, name="Std", price=Decimal("100.00"), quota=5, sold=0
    )
    web_session.add(ticket_type)
    await web_session.commit()
    return event, ticket_type


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_reserve_requires_auth(client: httpx.AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/orders",
        json={"event_id": str(uuid.uuid4()), "items": []},
    )
    assert resp.status_code == 401


async def test_reserve_decrements_free_tickets(
    client: httpx.AsyncClient,
    client_user: tuple[uuid.UUID, str],
    on_sale_event: tuple[Event, TicketType],
) -> None:
    user_id, token = client_user
    event, ticket_type = on_sale_event

    resp = await client.post(
        "/api/v1/orders",
        headers=_auth(token),
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(ticket_type.id), "quantity": 2}],
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "reserved"
    assert body["total_amount"] == "200.00"
    assert len(body["tickets"]) == 2

    detail = await client.get(f"/api/v1/events/{event.id}")
    assert detail.json()["free_tickets"] == 3

    orders = await client.get("/api/v1/orders", headers=_auth(token))
    assert orders.status_code == 200
    assert orders.json()["total"] == 1


async def test_sold_out(
    client: httpx.AsyncClient,
    client_user: tuple[uuid.UUID, str],
    on_sale_event: tuple[Event, TicketType],
) -> None:
    user_id, token = client_user
    event, ticket_type = on_sale_event

    first = await client.post(
        "/api/v1/orders",
        headers=_auth(token),
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(ticket_type.id), "quantity": 1}],
        },
    )
    assert first.status_code == 201

    second = await client.post(
        "/api/v1/orders",
        headers=_auth(token),
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(ticket_type.id), "quantity": 5}],
        },
    )
    assert second.status_code == 409
    assert second.json()["code"] == "sold_out"


async def test_pay_and_cancel_paid_forbidden(
    client: httpx.AsyncClient,
    client_user: tuple[uuid.UUID, str],
    on_sale_event: tuple[Event, TicketType],
) -> None:
    user_id, token = client_user
    event, ticket_type = on_sale_event

    order = await client.post(
        "/api/v1/orders",
        headers=_auth(token),
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(ticket_type.id), "quantity": 1}],
        },
    )
    order_id = order.json()["id"]

    paid = await client.post(f"/api/v1/orders/{order_id}/pay", headers=_auth(token))
    assert paid.status_code == 200
    assert paid.json()["status"] == "paid"

    again = await client.post(f"/api/v1/orders/{order_id}/pay", headers=_auth(token))
    assert again.status_code == 409

    cancelled = await client.post(
        f"/api/v1/orders/{order_id}/cancel", headers=_auth(token)
    )
    assert cancelled.status_code == 409
    assert cancelled.json()["code"] == "paid_order_cannot_cancel"


async def test_cancel_reserved_releases_quota(
    client: httpx.AsyncClient,
    client_user: tuple[uuid.UUID, str],
    on_sale_event: tuple[Event, TicketType],
) -> None:
    user_id, token = client_user
    event, ticket_type = on_sale_event

    order = await client.post(
        "/api/v1/orders",
        headers=_auth(token),
        json={
            "event_id": str(event.id),
            "items": [{"ticket_type_id": str(ticket_type.id), "quantity": 2}],
        },
    )
    order_id = order.json()["id"]

    cancelled = await client.post(
        f"/api/v1/orders/{order_id}/cancel", headers=_auth(token)
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    detail = await client.get(f"/api/v1/events/{event.id}")
    assert detail.json()["free_tickets"] == 5


async def test_cleanup_expired_releases_quota(
    web_session: AsyncSession,
    client_user: tuple[uuid.UUID, str],
    on_sale_event: tuple[Event, TicketType],
) -> None:
    user_id, _ = client_user
    event, ticket_type = on_sale_event

    order = await OrderService(web_session).reserve(
        client_id=user_id,
        event_id=event.id,
        items=[OrderItem(ticket_type_id=ticket_type.id, quantity=3)],
    )
    order.reserved_until = datetime.now(UTC) - timedelta(minutes=1)
    await web_session.commit()

    released = await OrderService(web_session).cleanup_expired()
    assert released == 1

    refreshed = await OrderRepository(web_session).get_with_tickets(order.id)
    assert refreshed is not None
    assert refreshed.status.value == "cancelled"
    ticket_type_db = await web_session.get(TicketType, ticket_type.id)
    assert ticket_type_db.sold == 0


async def test_concurrent_reserve_no_oversell(
    client: httpx.AsyncClient,
    client_user: tuple[uuid.UUID, str],
    on_sale_event: tuple[Event, TicketType],
) -> None:
    user_id, token = client_user
    event, ticket_type = on_sale_event

    async def reserve_once() -> int:
        resp = await client.post(
            "/api/v1/orders",
            headers=_auth(token),
            json={
                "event_id": str(event.id),
                "items": [{"ticket_type_id": str(ticket_type.id), "quantity": 1}],
            },
        )
        return resp.status_code

    results = await asyncio.gather(*[reserve_once() for _ in range(10)])
    ok = sum(1 for r in results if r == 201)
    sold_out = sum(1 for r in results if r == 409)
    assert ok == 5
    assert sold_out == 5

    detail = await client.get(f"/api/v1/events/{event.id}")
    assert detail.json()["free_tickets"] == 0


async def test_concurrent_cleanup_no_double_release(
    web_session: AsyncSession,
    client_user: tuple[uuid.UUID, str],
    on_sale_event: tuple[Event, TicketType],
    pg_engine: AsyncEngine,
) -> None:
    user_id, _ = client_user
    event, ticket_type = on_sale_event

    order = await OrderService(web_session).reserve(
        client_id=user_id,
        event_id=event.id,
        items=[OrderItem(ticket_type_id=ticket_type.id, quantity=3)],
    )
    order.reserved_until = datetime.now(UTC) - timedelta(minutes=1)
    await web_session.commit()

    factory = async_sessionmaker(pg_engine, expire_on_commit=False)
    async with factory() as s1, factory() as s2:
        await asyncio.gather(
            OrderService(s1).cleanup_expired(),
            OrderService(s2).cleanup_expired(),
        )

    await web_session.refresh(ticket_type, ["sold"])
    assert ticket_type.sold == 0


async def test_cleanup_vs_cancel_no_double_release(
    web_session: AsyncSession,
    client_user: tuple[uuid.UUID, str],
    on_sale_event: tuple[Event, TicketType],
    pg_engine: AsyncEngine,
) -> None:
    user_id, _ = client_user
    event, ticket_type = on_sale_event

    order = await OrderService(web_session).reserve(
        client_id=user_id,
        event_id=event.id,
        items=[OrderItem(ticket_type_id=ticket_type.id, quantity=3)],
    )
    order.reserved_until = datetime.now(UTC) - timedelta(minutes=1)
    await web_session.commit()

    factory = async_sessionmaker(pg_engine, expire_on_commit=False)
    async with factory() as s1, factory() as s2:
        await asyncio.gather(
            OrderService(s1).cleanup_expired(),
            OrderService(s2).cancel(order_id=order.id, client_id=user_id),
        )

    await web_session.refresh(ticket_type, ["sold"])
    assert ticket_type.sold == 0


async def test_cancel_already_cancelled_is_idempotent(
    web_session: AsyncSession,
    client_user: tuple[uuid.UUID, str],
    on_sale_event: tuple[Event, TicketType],
) -> None:
    user_id, _ = client_user
    event, ticket_type = on_sale_event

    order = await OrderService(web_session).reserve(
        client_id=user_id,
        event_id=event.id,
        items=[OrderItem(ticket_type_id=ticket_type.id, quantity=3)],
    )
    await OrderService(web_session).cancel(order_id=order.id, client_id=user_id)
    before = (await web_session.get(TicketType, ticket_type.id)).sold

    second = await OrderService(web_session).cancel(
        order_id=order.id, client_id=user_id
    )
    after = (await web_session.get(TicketType, ticket_type.id)).sold
    assert second.status.value == "cancelled"
    assert before == 0
    assert after == before
