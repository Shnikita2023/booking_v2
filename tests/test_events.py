import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

import httpx
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from booking.models.clients import InfoPage
from booking.models.events import Event, EventStatus

EventFactory = Callable[..., Awaitable[Event]]
PageFactory = Callable[..., Awaitable[InfoPage]]


@pytest_asyncio.fixture
async def event_factory(web_session: AsyncSession) -> EventFactory:
    async def make(
        *,
        title: str = "Excursion",
        status: EventStatus = EventStatus.ON_SALE,
        price: str | None = "1500.00",
        show_free: bool = False,
    ) -> Event:
        event = Event(
            title=title,
            starts_at=datetime.now(UTC) + timedelta(days=7),
            status=status,
            price=price,
            show_free_tickets=show_free,
            venue="Main hall",
            age_rating="12+",
        )
        web_session.add(event)
        await web_session.commit()
        return event

    return make


@pytest_asyncio.fixture
async def page_factory(web_session: AsyncSession) -> PageFactory:
    async def make(
        slug: str = "about", title: str = "About", content: str = "Text"
    ) -> InfoPage:
        page = InfoPage(slug=slug, title=title, content=content)
        web_session.add(page)
        await web_session.commit()
        return page

    return make


async def test_afisha_lists_only_on_sale(
    client: httpx.AsyncClient, event_factory: EventFactory
) -> None:
    on_sale = await event_factory(title="Visible")
    await event_factory(title="Draft", status=EventStatus.DRAFT)
    await event_factory(title="Paused", status=EventStatus.PAUSED)

    resp = await client.get("/api/v1/events")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert [item["title"] for item in body["items"]] == ["Visible"]
    assert str(on_sale.id) == body["items"][0]["id"]


async def test_soft_deleted_event_hidden_from_list_and_detail(
    client: httpx.AsyncClient,
    web_session: AsyncSession,
    event_factory: EventFactory,
) -> None:
    event = await event_factory()
    event.deleted_at = datetime.now(UTC)
    await web_session.commit()

    list_resp = await client.get("/api/v1/events")
    assert list_resp.json()["total"] == 0
    detail_resp = await client.get(f"/api/v1/events/{event.id}")
    assert detail_resp.status_code == 404
    assert detail_resp.json()["code"] == "event_not_found"


async def test_pagination(
    client: httpx.AsyncClient, event_factory: EventFactory
) -> None:
    for i in range(3):
        await event_factory(title=f"Event {i}")
    first_page = await client.get("/api/v1/events?limit=2&offset=0")
    body = first_page.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2
    second_page = await client.get("/api/v1/events?limit=2&offset=2")
    titles = {item["title"] for item in second_page.json()["items"]}
    assert len(titles) == 1


async def test_event_detail_decimal_price_as_string(
    client: httpx.AsyncClient, event_factory: EventFactory
) -> None:
    event = await event_factory(price="1500.00")
    resp = await client.get(f"/api/v1/events/{event.id}")
    assert resp.status_code == 200
    raw = resp.text
    assert "1500.00" in raw
    assert "1500.0" not in raw.replace("1500.00", "")
    body = resp.json()
    assert body["status"] == "on_sale"
    assert body["sale_paused"] is False


async def test_event_not_found(client: httpx.AsyncClient) -> None:
    resp = await client.get(f"/api/v1/events/{uuid.uuid4()}")
    assert resp.status_code == 404
    assert resp.json()["code"] == "event_not_found"


async def test_validation_error_on_bad_limit(client: httpx.AsyncClient) -> None:
    bad_low = await client.get("/api/v1/events?limit=0")
    assert bad_low.status_code == 422
    bad_high = await client.get("/api/v1/events?limit=101")
    assert bad_high.status_code == 422


async def test_info_page_by_slug(
    client: httpx.AsyncClient, page_factory: PageFactory
) -> None:
    await page_factory(slug="rules", title="Rules", content="Be polite")
    resp = await client.get("/api/v1/pages/rules")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"slug": "rules", "title": "Rules", "content": "Be polite"}
    missing = await client.get("/api/v1/pages/nope")
    assert missing.status_code == 404
    assert missing.json()["code"] == "page_not_found"
