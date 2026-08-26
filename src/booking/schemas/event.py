import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ListQuery(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class EventShort(BaseModel):
    id: uuid.UUID
    title: str
    starts_at: datetime
    venue: str | None
    age_rating: str | None
    banner_small_url: str | None
    free_tickets: int | None


class EventListResponse(BaseModel):
    items: list[EventShort]
    total: int


class EventDetail(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    starts_at: datetime
    duration_min: int | None
    age_rating: str | None
    venue: str | None
    price: Decimal | None
    status: str
    banner_small_url: str | None
    banner_large_url: str | None
    show_free_tickets: bool
    sale_paused: bool
    free_tickets: int | None


class PageResponse(BaseModel):
    slug: str
    title: str
    content: str
