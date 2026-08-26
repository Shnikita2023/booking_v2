import httpx

from booking.main import app


async def test_health_ok(client: httpx.AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["db"] == "ok"
    assert "version" in body
    assert app  # app builds


async def test_health_has_request_id(client: httpx.AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.headers.get("x-request-id")
