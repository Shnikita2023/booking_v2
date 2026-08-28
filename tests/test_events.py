import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx
import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from booking.models.clients import InfoPage
from booking.models.events import Event, EventStatus, TicketType
from booking.repositories.event import EventRepository
from booking.services.event_service import EventService

EventFactory = Callable[..., Awaitable[Event]]
PageFactory = Callable[..., Awaitable[InfoPage]]


@pytest.fixture
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


@pytest.fixture
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


async def test_event_price_is_derived_from_ticket_types_bc(
    web_session: AsyncSession, event_factory: EventFactory
) -> None:
    event = await event_factory(price=None)
    assert event.price is None

    for value in (Decimal("2000.00"), Decimal("999.00"), Decimal("1500.00")):
        web_session.add(
            TicketType(event_id=event.id, name="Тариф", price=value, quota=10)
        )
    await web_session.commit()

    await EventService(web_session).sync_price(event)

    refreshed = await EventRepository(web_session).get(event.id)
    assert refreshed is not None
    assert refreshed.price == Decimal("999.00")


async def test_free_tickets_bulk(db_session: AsyncSession) -> None:
    repo = EventRepository(db_session)
    ev1 = Event(
        title="E1",
        starts_at=datetime.now(UTC) + timedelta(days=1),
        status=EventStatus.ON_SALE,
        price=None,
        show_free_tickets=True,
        venue="V",
    )
    ev2 = Event(
        title="E2",
        starts_at=datetime.now(UTC) + timedelta(days=1),
        status=EventStatus.ON_SALE,
        price=None,
        show_free_tickets=True,
        venue="V",
    )
    db_session.add_all([ev1, ev2])
    await db_session.flush()
    db_session.add_all(
        [
            TicketType(event_id=ev1.id, name="a", price=Decimal("10"), quota=5, sold=2),
            TicketType(event_id=ev1.id, name="b", price=Decimal("10"), quota=3, sold=1),
            TicketType(event_id=ev2.id, name="c", price=Decimal("10"), quota=10, sold=10),
        ]
    )
    await db_session.commit()

    assert await repo.free_tickets_bulk([ev1.id, ev2.id]) == {ev1.id: 5, ev2.id: 0}
    assert await repo.free_tickets_bulk([]) == {}


async def test_catalog_list_free_tickets_and_no_nplus1(
    client: httpx.AsyncClient,
    web_session: AsyncSession,
    pg_engine: object,
    event_factory: EventFactory,
) -> None:
    for i in range(12):
        event = await event_factory(title=f"E{i}", show_free=(i % 2 == 0))
        if i % 2 == 0:
            web_session.add(
                TicketType(event_id=event.id, name="t", price=Decimal("10"), quota=10, sold=3)
            )
    await web_session.commit()

    counter = {"n": 0}

    def _inc(*args: object, **kwargs: object) -> None:
        counter["n"] += 1

    sa.event.listen(pg_engine.sync_engine, "after_cursor_execute", _inc)  # type: ignore[attr-defined]
    try:
        counter["n"] = 0
        resp = await client.get("/api/v1/events")
        assert resp.status_code == 200
        # 2 queries for the list + 1 bulk free-ticket query; NOT 2 + 12 (N+1).
        assert counter["n"] < 10
    finally:
        sa.event.remove(pg_engine.sync_engine, "after_cursor_execute", _inc)  # type: ignore[attr-defined]

    body = resp.json()
    by_title = {item["title"]: item for item in body["items"]}
    assert by_title["E0"]["free_tickets"] == 7
    assert by_title["E1"]["free_tickets"] is None
