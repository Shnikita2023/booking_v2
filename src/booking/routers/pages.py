"""Static information page endpoints."""

from fastapi import APIRouter

from booking.core.deps import SessionDep
from booking.schemas.event import PageResponse
from booking.services.event_service import EventService

router = APIRouter(prefix="/api/v1/pages", tags=["pages"])


@router.get(
    "/{slug}",
    summary="Information page",
    description="Return a static information page by its slug.",
    response_model=PageResponse,
)
async def get_page(slug: str, session: SessionDep) -> PageResponse:
    page = await EventService(session).get_page(slug)
    return PageResponse(slug=page.slug, title=page.title, content=page.content)
