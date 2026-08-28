"""Audit journal tests (step 7) against a real Postgres container."""

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from booking.core.dto import Principal
from booking.models.audit import AuditAction
from booking.models.clients import Client, UserType
from booking.models.users import RoleCode
from booking.repositories.clients import ClientRepository
from booking.services import security
from booking.services.audit_service import AuditService

FUTURE = datetime(2030, 5, 1, 18, 0, tzinfo=UTC)


def _headers(
    subject: str, user_type: str = "system_user", role: str | None = None
) -> dict[str, str]:
    extra = {"ut": user_type}
    if role is not None:
        extra["role"] = role
    token, _ = security.create_token("access", subject, extra_claims=extra)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def client_user(web_session: object) -> Client:
    client = await ClientRepository(web_session).create(  # type: ignore[arg-type]
        email="auditcust@example.com",
        full_name="Cust",
        phone=None,
        password_hash=security.hash_password("strongpass123"),
        is_active=True,
        discount_percent=0,
    )
    await web_session.commit()  # type: ignore[attr-defined]
    return client


async def test_audit_search_filters_and_ordering(db_session: object) -> None:
    svc = AuditService(db_session)  # type: ignore[arg-type]
    await svc.record(
        action=AuditAction.EVENT_CREATE,
        entity_type="event",
        entity_id=uuid.uuid4(),
        actor=Principal(user_type=UserType.CLIENT, user_id=uuid.uuid4()),
    )
    await svc.record(
        action=AuditAction.ORDER_RESERVE,
        entity_type="order",
        entity_id=uuid.uuid4(),
        actor=None,
    )
    await db_session.commit()  # type: ignore[attr-defined]

    by_action, total = await svc.search(action=AuditAction.EVENT_CREATE)
    assert total == 1
    by_entity, total = await svc.search(entity_type="order")
    assert total == 1

    all_items, total = await svc.search()
    assert total == 2
    assert all_items[0].created_at >= all_items[1].created_at

    page, total = await svc.search(limit=1, offset=0)
    assert len(page) == 1 and total == 2


async def test_admin_event_creation_is_audited(
    client: AsyncClient, staff_user: dict[str, str]
) -> None:
    headers = _headers(staff_user["id"], role=RoleCode.ADMIN.value)
    created = (
        await client.post(
            "/api/v1/admin/events",
            headers=headers,
            json={"title": "Audited", "starts_at": FUTURE.isoformat(), "sale_paused": False},
        )
    ).json()

    audit = await client.get(
        "/api/v1/admin/audit", headers=headers, params={"action": "event_create"}
    )
    assert audit.status_code == 200, audit.text
    body = audit.json()
    assert body["total"] == 1
    entry = body["items"][0]
    assert entry["actor_type"] == "system_user"
    assert entry["actor_role"] == "admin"
    assert entry["entity_id"] == created["id"]


async def test_client_order_reserve_is_audited(
    client: AsyncClient, staff_user: dict[str, str]
) -> None:
    admin = _headers(staff_user["id"], role=RoleCode.ADMIN.value)
    ev = (
        await client.post(
            "/api/v1/admin/events",
            headers=admin,
            json={
                "title": "Show",
                "starts_at": FUTURE.isoformat(),
                "sale_paused": False,
                "ticket_types": [{"name": "S", "price": "10.00", "quota": 5}],
            },
        )
    ).json()
    await client.post(f"/api/v1/admin/events/{ev['id']}/publish", headers=admin)
    tts = (
        await client.get(f"/api/v1/admin/events/{ev['id']}/ticket-types", headers=admin)
    ).json()["items"]
    tt_id = tts[0]["id"]

    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "buyer@example.com", "password": "strongpass123", "full_name": "B"},
    )
    assert reg.status_code == 201
    login = (
        await client.post(
            "/api/v1/auth/login", json={"email": "buyer@example.com", "password": "strongpass123"}
        )
    ).json()
    buyer = {"Authorization": f"Bearer {login['access_token']}"}

    order = await client.post(
        "/api/v1/orders",
        headers=buyer,
        json={"event_id": ev["id"], "items": [{"ticket_type_id": tt_id, "quantity": 1}]},
    )
    assert order.status_code == 201, order.text

    audit = await client.get(
        "/api/v1/admin/audit", headers=admin, params={"action": "order_reserve"}
    )
    assert audit.json()["total"] == 1
    entry = audit.json()["items"][0]
    assert entry["actor_type"] == "client"
    assert entry["entity_type"] == "order"
    assert entry["entity_id"] == order.json()["id"]


async def test_failed_login_is_audited(client: AsyncClient, staff_user: dict[str, str]) -> None:
    admin = _headers(staff_user["id"], role=RoleCode.ADMIN.value)
    fail = await client.post(
        "/api/v1/auth/login", json={"email": "ghost@example.com", "password": "wrong"}
    )
    assert fail.status_code in (401, 403)

    audit = await client.get(
        "/api/v1/admin/audit", headers=admin, params={"action": "auth_login_fail"}
    )
    assert audit.json()["total"] == 1
    assert audit.json()["items"][0]["actor_type"] is None


async def test_audit_read_rbac(
    client: AsyncClient, staff_user: dict[str, str], client_user: Client
) -> None:
    admin = _headers(staff_user["id"], role=RoleCode.ADMIN.value)
    assert (await client.get("/api/v1/admin/audit", headers=admin)).status_code == 200

    buyer = _headers(str(client_user.id), user_type=UserType.CLIENT.value)
    assert (await client.get("/api/v1/admin/audit", headers=buyer)).status_code == 403
    assert (await client.get("/api/v1/admin/audit")).status_code == 401
