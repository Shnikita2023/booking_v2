"""Reports API tests (S-6) against a real Postgres container."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from booking.models.audit import AuditAction, AuditLog
from booking.models.clients import Client
from booking.models.events import Event, EventStatus, TicketType
from booking.models.orders import Order, OrderStatus, Payment, PaymentStatus, Ticket, TicketStatus
from booking.models.users import Role, RoleCode
from booking.repositories.clients import ClientRepository
from booking.repositories.users import SystemUserRepository
from booking.services import security

FUTURE = datetime(2030, 5, 1, 18, 0, tzinfo=UTC)
PAST = datetime(2025, 1, 1, 12, 0, tzinfo=UTC)


def _headers(
    subject: str,
    user_type: str = "system_user",
    role: str | None = None,
) -> dict[str, str]:
    extra = {"ut": user_type}
    if role is not None:
        extra["role"] = role
    token, _ = security.create_token("access", subject, extra_claims=extra)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def event_with_tickets(web_session: AsyncSession) -> Event:
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
    tt1 = TicketType(event_id=event.id, name="VIP", price=Decimal("500.00"), quota=10, sold=0)
    tt2 = TicketType(event_id=event.id, name="Standard", price=Decimal("100.00"), quota=50, sold=0)
    web_session.add_all([tt1, tt2])
    await web_session.flush()
    return event


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
    await web_session.flush()
    return client


async def _create_paid_order(
    session: AsyncSession,
    event: Event,
    client: Client,
    amount: Decimal,
    *,
    paid_at: datetime | None = None,
) -> Order:
    """Create a paid order with tickets and a succeeded payment."""
    order = Order(
        client_id=client.id,
        event_id=event.id,
        status=OrderStatus.PAID,
        total_amount=amount,
    )
    session.add(order)
    await session.flush()
    ticket = Ticket(
        order_id=order.id,
        ticket_type_id=event.ticket_types[0].id,
        price=amount,
        status=TicketStatus.ACTIVE,
    )
    session.add(ticket)
    payment = Payment(
        order_id=order.id,
        status=PaymentStatus.SUCCEEDED,
        amount=amount,
        method="card",
        currency="RUB",
        gateway="mock",
        paid_at=paid_at or datetime.now(UTC),
    )
    session.add(payment)
    await session.flush()
    return order


async def test_revenue_by_event(
    client: AsyncClient,
    staff_user: dict[str, str],
    web_session: AsyncSession,
    event_with_tickets: Event,
    buyer: Client,
) -> None:
    headers = _headers(staff_user["id"], role=RoleCode.ADMIN.value)
    await _create_paid_order(web_session, event_with_tickets, buyer, Decimal("500.00"))
    await _create_paid_order(web_session, event_with_tickets, buyer, Decimal("300.00"))
    await web_session.commit()

    resp = await client.get("/api/v1/staff/reports/revenue", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data) == 1
    assert data[0]["event_id"] == str(event_with_tickets.id)
    assert data[0]["event_title"] == "Concert"
    assert float(data[0]["total_revenue"]) == 800.0
    assert data[0]["payment_count"] == 2


async def test_revenue_by_date(
    client: AsyncClient,
    staff_user: dict[str, str],
    web_session: AsyncSession,
    event_with_tickets: Event,
    buyer: Client,
) -> None:
    headers = _headers(staff_user["id"], role=RoleCode.ADMIN.value)
    await _create_paid_order(
        web_session, event_with_tickets, buyer, Decimal("100.00"),
        paid_at=datetime(2026, 3, 15, 10, 0, tzinfo=UTC),
    )
    await _create_paid_order(
        web_session, event_with_tickets, buyer, Decimal("200.00"),
        paid_at=datetime(2026, 3, 15, 14, 0, tzinfo=UTC),
    )
    await _create_paid_order(
        web_session, event_with_tickets, buyer, Decimal("150.00"),
        paid_at=datetime(2026, 3, 16, 9, 0, tzinfo=UTC),
    )
    await web_session.commit()

    resp = await client.get("/api/v1/staff/reports/revenue-by-date", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data) == 2
    assert float(data[0]["total_revenue"]) == 300.0
    assert data[0]["payment_count"] == 2
    assert float(data[1]["total_revenue"]) == 150.0
    assert data[1]["payment_count"] == 1


async def test_revenue_by_date_filter(
    client: AsyncClient,
    staff_user: dict[str, str],
    web_session: AsyncSession,
    event_with_tickets: Event,
    buyer: Client,
) -> None:
    headers = _headers(staff_user["id"], role=RoleCode.ADMIN.value)
    await _create_paid_order(
        web_session, event_with_tickets, buyer, Decimal("100.00"),
        paid_at=datetime(2026, 3, 15, 10, 0, tzinfo=UTC),
    )
    await _create_paid_order(
        web_session, event_with_tickets, buyer, Decimal("200.00"),
        paid_at=datetime(2026, 3, 16, 10, 0, tzinfo=UTC),
    )
    await web_session.commit()

    resp = await client.get(
        "/api/v1/staff/reports/revenue-by-date",
        headers=headers,
        params={"from_date": "2026-03-16T00:00:00Z"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data) == 1
    assert float(data[0]["total_revenue"]) == 200.0


async def test_sales_by_status(
    client: AsyncClient,
    staff_user: dict[str, str],
    web_session: AsyncSession,
    event_with_tickets: Event,
    buyer: Client,
) -> None:
    headers = _headers(staff_user["id"], role=RoleCode.ADMIN.value)
    await _create_paid_order(web_session, event_with_tickets, buyer, Decimal("500.00"))
    # Add a reserved order
    order = Order(
        client_id=buyer.id,
        event_id=event_with_tickets.id,
        status=OrderStatus.RESERVED,
        total_amount=Decimal("100.00"),
    )
    web_session.add(order)
    await web_session.commit()

    resp = await client.get("/api/v1/staff/reports/sales", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    statuses = {r["status"] for r in data}
    assert "paid" in statuses
    assert "reserved" in statuses
    paid = next(r for r in data if r["status"] == "paid")
    assert paid["order_count"] == 1
    assert float(paid["total_amount"]) == 500.0


async def test_occupancy(
    client: AsyncClient,
    staff_user: dict[str, str],
    web_session: AsyncSession,
    event_with_tickets: Event,
    buyer: Client,
) -> None:
    headers = _headers(staff_user["id"], role=RoleCode.ADMIN.value)
    await _create_paid_order(web_session, event_with_tickets, buyer, Decimal("500.00"))
    # Update sold count on ticket type
    event_with_tickets.ticket_types[0].sold = 1
    await web_session.commit()

    resp = await client.get("/api/v1/staff/reports/occupancy", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data) == 1
    row = data[0]
    assert row["event_id"] == str(event_with_tickets.id)
    assert row["total_quota"] == 60
    assert row["total_sold"] == 1


async def test_top_clients(
    client: AsyncClient,
    staff_user: dict[str, str],
    web_session: AsyncSession,
    event_with_tickets: Event,
) -> None:
    headers = _headers(staff_user["id"], role=RoleCode.ADMIN.value)

    buyer1 = await ClientRepository(web_session).create(
        email="b1@example.com",
        full_name="Buyer1",
        password_hash=security.hash_password("pass123"),
        is_active=True,
        discount_percent=0,
    )
    buyer2 = await ClientRepository(web_session).create(
        email="b2@example.com",
        full_name="Buyer2",
        password_hash=security.hash_password("pass123"),
        is_active=True,
        discount_percent=0,
    )
    await web_session.flush()

    await _create_paid_order(web_session, event_with_tickets, buyer1, Decimal("500.00"))
    await _create_paid_order(web_session, event_with_tickets, buyer1, Decimal("300.00"))
    await _create_paid_order(web_session, event_with_tickets, buyer2, Decimal("200.00"))
    await web_session.commit()

    resp = await client.get("/api/v1/staff/reports/top-clients", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data) == 2
    assert data[0]["full_name"] == "Buyer1"
    assert float(data[0]["total_spent"]) == 800.0
    assert data[0]["total_orders"] == 2
    assert data[1]["full_name"] == "Buyer2"
    assert float(data[1]["total_spent"]) == 200.0


async def test_top_clients_pagination(
    client: AsyncClient,
    staff_user: dict[str, str],
    web_session: AsyncSession,
    event_with_tickets: Event,
) -> None:
    headers = _headers(staff_user["id"], role=RoleCode.ADMIN.value)
    buyers = []
    for i in range(5):
        b = await ClientRepository(web_session).create(
            email=f"p{i}@example.com",
            full_name=f"P{i}",
            password_hash=security.hash_password("pass123"),
            is_active=True,
            discount_percent=0,
        )
        buyers.append(b)
    await web_session.flush()

    for i, b in enumerate(buyers):
        await _create_paid_order(
            web_session, event_with_tickets, b, Decimal(f"{(i + 1) * 100}.00")
        )
    await web_session.commit()

    resp = await client.get(
        "/api/v1/staff/reports/top-clients",
        headers=headers,
        params={"limit": 2, "offset": 0},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data) == 2
    assert data[0]["full_name"] == "P4"

    resp2 = await client.get(
        "/api/v1/staff/reports/top-clients",
        headers=headers,
        params={"limit": 2, "offset": 2},
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert len(data2) == 2
    assert data2[0]["full_name"] == "P2"


async def test_audit_stats(
    client: AsyncClient,
    staff_user: dict[str, str],
    web_session: AsyncSession,
    event_with_tickets: Event,
    buyer: Client,
) -> None:
    headers = _headers(staff_user["id"], role=RoleCode.ADMIN.value)

    log1 = AuditLog(
        action=AuditAction.AUTH_LOGIN_OK,
        actor_role=RoleCode.ADMIN,
        entity_type=None,
        entity_id=None,
    )
    log2 = AuditLog(
        action=AuditAction.AUTH_LOGIN_OK,
        actor_role=RoleCode.ADMIN,
        entity_type=None,
        entity_id=None,
    )
    log3 = AuditLog(
        action=AuditAction.EVENT_CREATE,
        actor_role=RoleCode.ADMIN,
        entity_type="event",
        entity_id=event_with_tickets.id,
    )
    web_session.add_all([log1, log2, log3])
    await web_session.commit()

    resp = await client.get("/api/v1/staff/reports/audit-stats", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data) == 2
    login = next(r for r in data if r["action"] == "auth_login_ok")
    assert login["count"] == 2
    assert login["actor_role"] == "admin"


async def test_audit_stats_date_filter(
    client: AsyncClient,
    staff_user: dict[str, str],
    web_session: AsyncSession,
) -> None:
    headers = _headers(staff_user["id"], role=RoleCode.ADMIN.value)

    log1 = AuditLog(
        action=AuditAction.AUTH_LOGIN_OK,
        actor_role=RoleCode.ADMIN,
        entity_type=None,
        entity_id=None,
    )
    log1.created_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    log2 = AuditLog(
        action=AuditAction.EVENT_CREATE,
        actor_role=RoleCode.ADMIN,
        entity_type=None,
        entity_id=None,
    )
    log2.created_at = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
    web_session.add_all([log1, log2])
    await web_session.commit()

    resp = await client.get(
        "/api/v1/staff/reports/audit-stats",
        headers=headers,
        params={"from_date": "2026-03-01T00:00:00Z"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data) == 1
    assert data[0]["action"] == "event_create"


async def test_reports_forbidden_for_cashier(
    client: AsyncClient,
    staff_user: dict[str, str],
    web_session: AsyncSession,
) -> None:
    # Create a cashier role
    cashier_role = Role(code=RoleCode.CASHIER, name="Cashier")
    web_session.add(cashier_role)
    await web_session.flush()
    user = await SystemUserRepository(web_session).create(
        email="cashier_test@example.com",
        password_hash=security.hash_password("pass123"),
        role_id=cashier_role.id,
    )
    await web_session.commit()
    headers = _headers(str(user.id), role=RoleCode.CASHIER.value)

    for endpoint in [
        "/api/v1/staff/reports/revenue",
        "/api/v1/staff/reports/revenue-by-date",
        "/api/v1/staff/reports/sales",
        "/api/v1/staff/reports/occupancy",
        "/api/v1/staff/reports/top-clients",
        "/api/v1/staff/reports/audit-stats",
    ]:
        resp = await client.get(endpoint, headers=headers)
        assert resp.status_code == 403, f"Expected 403 for {endpoint}, got {resp.status_code}"


async def test_reports_unauthenticated(client: AsyncClient) -> None:
    for endpoint in [
        "/api/v1/staff/reports/revenue",
        "/api/v1/staff/reports/revenue-by-date",
        "/api/v1/staff/reports/sales",
        "/api/v1/staff/reports/occupancy",
        "/api/v1/staff/reports/top-clients",
        "/api/v1/staff/reports/audit-stats",
    ]:
        resp = await client.get(endpoint)
        assert resp.status_code == 401, f"Expected 401 for {endpoint}, got {resp.status_code}"


async def test_empty_reports(
    client: AsyncClient,
    staff_user: dict[str, str],
) -> None:
    headers = _headers(staff_user["id"], role=RoleCode.ADMIN.value)
    for endpoint in [
        "/api/v1/staff/reports/revenue",
        "/api/v1/staff/reports/revenue-by-date",
        "/api/v1/staff/reports/sales",
        "/api/v1/staff/reports/occupancy",
        "/api/v1/staff/reports/top-clients",
        "/api/v1/staff/reports/audit-stats",
    ]:
        resp = await client.get(endpoint, headers=headers)
        assert resp.status_code == 200, resp.text
        assert resp.json() == []
