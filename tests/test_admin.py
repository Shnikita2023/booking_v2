"""Admin API tests (S-2/S-3/S-8) against a real Postgres container."""

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from booking.models.clients import Client, UserType
from booking.models.users import RoleCode
from booking.repositories.clients import ClientRepository
from booking.repositories.event import TicketTypeRepository
from booking.services import security

FUTURE = datetime(2030, 5, 1, 18, 0, tzinfo=UTC)


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
async def client_user(web_session: AsyncSession) -> Client:
    client = await ClientRepository(web_session).create(
        email="cust@example.com",
        full_name="Cust",
        phone=None,
        password_hash=security.hash_password("strongpass123"),
        is_active=True,
        discount_percent=0,
    )
    await web_session.commit()
    return client


async def test_create_event_syncs_price_and_lists(
    client: AsyncClient, staff_user: dict[str, str]
) -> None:
    headers = _headers(staff_user["id"], role=RoleCode.ADMIN.value)
    resp = await client.post(
        "/api/v1/admin/events",
        headers=headers,
        json={
            "title": "Concert",
            "starts_at": FUTURE.isoformat(),
            "show_free_tickets": False,
            "sale_paused": False,
            "ticket_types": [
                {"name": "VIP", "price": "50.00", "quota": 10},
                {"name": "Standard", "price": "20.00", "quota": 100},
            ],
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "draft"
    assert float(body["price"]) == 20.0

    list_resp = await client.get("/api/v1/admin/events", headers=headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == 1


async def test_event_lifecycle_actions(
    client: AsyncClient, staff_user: dict[str, str]
) -> None:
    headers = _headers(staff_user["id"], role=RoleCode.ADMIN.value)
    created = (
        await client.post(
            "/api/v1/admin/events",
            headers=headers,
            json={"title": "Play", "starts_at": FUTURE.isoformat(), "sale_paused": False},
        )
    ).json()
    event_id = created["id"]

    resp = await client.post(f"/api/v1/admin/events/{event_id}/publish", headers=headers)
    assert resp.json()["status"] == "on_sale"

    paused = await client.post(f"/api/v1/admin/events/{event_id}/pause-sales", headers=headers)
    assert paused.json()["sale_paused"] is True
    assert paused.json()["status"] == "on_sale"

    resumed = await client.post(f"/api/v1/admin/events/{event_id}/resume-sales", headers=headers)
    assert resumed.json()["sale_paused"] is False

    moved = await client.post(
        f"/api/v1/admin/events/{event_id}/move",
        headers=headers,
        json={"starts_at": datetime(2031, 1, 1, tzinfo=UTC).isoformat()},
    )
    assert moved.json()["status"] == "moved"

    cancelled = await client.post(f"/api/v1/admin/events/{event_id}/cancel", headers=headers)
    assert cancelled.json()["status"] == "cancelled"


async def test_event_complete_from_on_sale(
    client: AsyncClient, staff_user: dict[str, str]
) -> None:
    """Test that ON_SALE → COMPLETED transition works."""
    headers = _headers(staff_user["id"], role=RoleCode.ADMIN.value)
    created = (
        await client.post(
            "/api/v1/admin/events",
            headers=headers,
            json={"title": "Festival", "starts_at": FUTURE.isoformat(), "sale_paused": False},
        )
    ).json()
    event_id = created["id"]

    resp = await client.post(f"/api/v1/admin/events/{event_id}/publish", headers=headers)
    assert resp.json()["status"] == "on_sale"

    completed = await client.post(f"/api/v1/admin/events/{event_id}/complete", headers=headers)
    assert completed.json()["status"] == "completed"


async def test_event_invalid_transition_rejected(
    client: AsyncClient, staff_user: dict[str, str]
) -> None:
    """Test that invalid status transitions are rejected."""
    headers = _headers(staff_user["id"], role=RoleCode.ADMIN.value)
    created = (
        await client.post(
            "/api/v1/admin/events",
            headers=headers,
            json={"title": "Concert2", "starts_at": FUTURE.isoformat(), "sale_paused": False},
        )
    ).json()
    event_id = created["id"]

    # DRAFT → CANCELLED is allowed
    cancelled = await client.post(f"/api/v1/admin/events/{event_id}/cancel", headers=headers)
    assert cancelled.json()["status"] == "cancelled"

    # CANCELLED → ON_SALE should be rejected
    resp = await client.post(f"/api/v1/admin/events/{event_id}/publish", headers=headers)
    assert resp.status_code == 409


async def test_clone_event_copies_ticket_types(
    client: AsyncClient, staff_user: dict[str, str]
) -> None:
    headers = _headers(staff_user["id"], role=RoleCode.ADMIN.value)
    created = (
        await client.post(
            "/api/v1/admin/events",
            headers=headers,
            json={
                "title": "Fest",
                "starts_at": FUTURE.isoformat(),
                "ticket_types": [{"name": "A", "price": "10.00", "quota": 5}],
            },
        )
    ).json()
    cloned = (
        await client.post(f"/api/v1/admin/events/{created['id']}/clone", headers=headers)
    ).json()
    assert cloned["id"] != created["id"]
    assert cloned["status"] == "draft"
    assert cloned["cloned_from_id"] == created["id"]

    tts = (
        await client.get(f"/api/v1/admin/events/{cloned['id']}/ticket-types", headers=headers)
    ).json()["items"]
    assert len(tts) == 1 and tts[0]["sold"] == 0


async def test_ticket_type_quota_guard(
    client: AsyncClient, staff_user: dict[str, str], web_session: AsyncSession
) -> None:
    headers = _headers(staff_user["id"], role=RoleCode.ADMIN.value)
    created = (
        await client.post(
            "/api/v1/admin/events",
            headers=headers,
            json={
                "title": "Show",
                "starts_at": FUTURE.isoformat(),
                "ticket_types": [{"name": "A", "price": "10.00", "quota": 10}],
            },
        )
    ).json()
    tts = (
        await client.get(f"/api/v1/admin/events/{created['id']}/ticket-types", headers=headers)
    ).json()["items"]
    tt_id = tts[0]["id"]

    repo = TicketTypeRepository(web_session)
    ticket_type = await repo.get(uuid.UUID(tt_id))
    await repo.update(ticket_type, sold=3)
    await web_session.commit()

    bad = await client.put(
        f"/api/v1/admin/events/{created['id']}/ticket-types/{tt_id}",
        headers=headers,
        json={"quota": 2},
    )
    assert bad.status_code == 409

    delete_blocked = await client.delete(
        f"/api/v1/admin/events/{created['id']}/ticket-types/{tt_id}", headers=headers
    )
    assert delete_blocked.status_code == 409

    ok = await client.put(
        f"/api/v1/admin/events/{created['id']}/ticket-types/{tt_id}",
        headers=headers,
        json={"quota": 5},
    )
    assert ok.status_code == 200


async def test_admin_event_rbac(
    client: AsyncClient, staff_user: dict[str, str], client_user: Client
) -> None:
    admin_headers = _headers(staff_user["id"], role=RoleCode.ADMIN.value)
    resp = await client.get("/api/v1/admin/events", headers=admin_headers)
    assert resp.status_code == 200

    client_headers = _headers(str(client_user.id), user_type=UserType.CLIENT.value)
    resp = await client.get("/api/v1/admin/events", headers=client_headers)
    assert resp.status_code == 403
    assert (await client.get("/api/v1/admin/events")).status_code == 401


async def test_client_management_crud(
    client: AsyncClient, staff_user: dict[str, str]
) -> None:
    headers = _headers(staff_user["id"], role=RoleCode.MANAGER.value)
    created = (
        await client.post(
            "/api/v1/admin/clients",
            headers=headers,
            json={"email": "new@example.com", "password": "strongpass123", "full_name": "New"},
        )
    ).json()
    client_id = created["id"]
    assert created["is_active"] is True

    updated = await client.put(
        f"/api/v1/admin/clients/{client_id}",
        headers=headers,
        json={"full_name": "Renamed", "discount_percent": 5},
    )
    data = updated.json()
    assert data["full_name"] == "Renamed" and data["discount_percent"] == 5

    blocked = await client.post(f"/api/v1/admin/clients/{client_id}/block", headers=headers)
    assert blocked.json()["is_active"] is False
    unblocked = await client.post(f"/api/v1/admin/clients/{client_id}/unblock", headers=headers)
    assert unblocked.json()["is_active"] is True

    reset = await client.post(
        f"/api/v1/admin/clients/{client_id}/reset-password",
        headers=headers,
        json={"password": "anotherpass123"},
    )
    assert reset.status_code == 204

    deleted = await client.delete(f"/api/v1/admin/clients/{client_id}", headers=headers)
    assert deleted.status_code == 204
    missing = await client.get(f"/api/v1/admin/clients/{client_id}", headers=headers)
    assert missing.status_code == 404


async def test_system_user_management(
    client: AsyncClient, staff_user: dict[str, str]
) -> None:
    headers = _headers(staff_user["id"], role=RoleCode.ADMIN.value)
    created = (
        await client.post(
            "/api/v1/admin/users",
            headers=headers,
            json={"email": "mgr@example.com", "password": "strongpass123", "role_code": "manager"},
        )
    ).json()
    user_id = created["id"]
    assert created["role_code"] == "manager"

    updated = await client.put(
        f"/api/v1/admin/users/{user_id}",
        headers=headers,
        json={"is_active": False, "role_code": "cashier"},
    )
    data = updated.json()
    assert data["is_active"] is False and data["role_code"] == "cashier"

    unblocked = await client.post(f"/api/v1/admin/users/{user_id}/unblock", headers=headers)
    assert unblocked.json()["is_active"] is True
    deleted = await client.delete(f"/api/v1/admin/users/{user_id}", headers=headers)
    assert deleted.status_code == 204
    missing = await client.get(f"/api/v1/admin/users/{user_id}", headers=headers)
    assert missing.status_code == 404


async def test_system_users_admin_only(
    client: AsyncClient, staff_user: dict[str, str], client_user: Client
) -> None:
    admin_headers = _headers(staff_user["id"], role=RoleCode.ADMIN.value)
    manager = (
        await client.post(
            "/api/v1/admin/users",
            headers=admin_headers,
            json={"email": "mgr2@example.com", "password": "strongpass123", "role_code": "manager"},
        )
    ).json()
    manager_headers = _headers(manager["id"], role=RoleCode.MANAGER.value)
    resp = await client.get("/api/v1/admin/users", headers=manager_headers)
    assert resp.status_code == 403

    client_headers = _headers(str(client_user.id), user_type=UserType.CLIENT.value)
    resp = await client.get("/api/v1/admin/users", headers=client_headers)
    assert resp.status_code == 403


async def test_settings_json_roundtrip(
    client: AsyncClient, staff_user: dict[str, str]
) -> None:
    headers = _headers(staff_user["id"], role=RoleCode.ADMIN.value)
    value = {"days": 14, "allowed": True}
    put = await client.put(
        "/api/v1/admin/settings/refund_policy",
        headers=headers,
        json={"key": "refund_policy", "value": value, "description": "Refund rules"},
    )
    assert put.status_code == 200, put.text
    assert put.json()["value"] == value

    got = await client.get("/api/v1/admin/settings/refund_policy", headers=headers)
    assert got.json()["value"] == value

    listed = await client.get("/api/v1/admin/settings", headers=headers)
    assert any(s["key"] == "refund_policy" for s in listed.json())
