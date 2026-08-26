import httpx
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from booking.repositories.tokens import RefreshTokenRepository
from booking.services.auth_service import AuthService


@pytest_asyncio.fixture
async def auth_service(db_session: AsyncSession) -> AuthService:
    return AuthService(db_session)


@pytest_asyncio.fixture
async def token_repo(db_session: AsyncSession) -> RefreshTokenRepository:
    return RefreshTokenRepository(db_session)


async def _register(client: AsyncClient, email: str = "user1@example.com") -> dict[str, str]:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "strongpass123", "full_name": "Test"},
    )
    assert resp.status_code == 201
    body: dict[str, str] = resp.json()
    return body


async def _login(
    client: AsyncClient, email: str, password: str
) -> httpx.Response:
    return await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )


async def test_register_login_me_flow(client: AsyncClient) -> None:
    registered = await _register(client)
    assert registered["email"] == "user1@example.com"

    login_resp = await _login(client, "user1@example.com", "strongpass123")
    assert login_resp.status_code == 200
    tokens = login_resp.json()
    assert tokens["token_type"] == "bearer"
    assert "access_token" in tokens and "refresh_token" in tokens

    me_resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert me_resp.status_code == 200
    body = me_resp.json()
    assert body["user_type"] == "client"
    assert body["id"] == registered["id"]

    refresh_resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh_resp.status_code == 200

    logout_resp = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {refresh_resp.json()['access_token']}"},
    )
    assert logout_resp.status_code == 204


async def test_duplicate_email_conflict(client: AsyncClient) -> None:
    await _register(client, "dup@example.com")
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "dup@example.com", "password": "strongpass123"},
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "email_taken"


async def test_wrong_password_401(client: AsyncClient) -> None:
    await _register(client, "wrongpw@example.com")
    resp = await _login(client, "wrongpw@example.com", "badpassword")
    assert resp.status_code == 401
    assert resp.json()["code"] == "invalid_credentials"


async def test_lockout_after_three_failures(client: AsyncClient) -> None:
    await _register(client, "lock@example.com")
    for attempt in range(3):
        resp = await _login(client, "lock@example.com", "badpassword")
        expected_status = 403 if attempt == 2 else 401
        assert resp.status_code == expected_status
    # Even correct password is rejected while locked
    locked_resp = await _login(client, "lock@example.com", "strongpass123")
    assert locked_resp.status_code == 403
    assert locked_resp.json()["code"] == "account_locked"


async def test_staff_login_and_single_session(
    client: AsyncClient, staff_user: dict[str, str]
) -> None:
    first = await client.post(
        "/api/v1/staff/login",
        json={"email": staff_user["email"], "password": "staffpass123"},
    )
    assert first.status_code == 200
    second = await client.post(
        "/api/v1/staff/login",
        json={"email": staff_user["email"], "password": "staffpass123"},
    )
    assert second.status_code == 200

    # First session's refresh token must be revoked by the second login
    rotated_first = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first.json()["refresh_token"]},
    )
    assert rotated_first.status_code == 401

    # Second session still works; role claim present for /me
    me_resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {second.json()['access_token']}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["role"] == "admin"


async def test_refresh_with_access_token_rejected(client: AsyncClient) -> None:
    await _register(client, "rtar@example.com")
    tokens = (await _login(client, "rtar@example.com", "strongpass123")).json()
    resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["access_token"]}
    )
    assert resp.status_code == 401


async def test_me_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


async def test_garbage_token_401(client: AsyncClient) -> None:
    resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-jwt"}
    )
    assert resp.status_code == 401
