"""Admin schemas for events and ticket types."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from booking.models.events import Event, EventStatus, TicketType


class TicketTypeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    name: str
    price: Decimal
    quota: int
    sold: int
    deleted_at: datetime | None = None

    @classmethod
    def from_ticket_type(cls, ticket_type: TicketType) -> "TicketTypeRead":
        return cls(
            id=ticket_type.id,
            event_id=ticket_type.event_id,
            name=ticket_type.name,
            price=ticket_type.price,
            quota=ticket_type.quota,
            sold=ticket_type.sold,
            deleted_at=ticket_type.deleted_at,
        )


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None = None
    starts_at: datetime
    duration_min: int | None = None
    age_rating: str | None = None
    venue: str | None = None
    price: Decimal | None = None
    status: EventStatus
    banner_small_url: str | None = None
    banner_large_url: str | None = None
    show_free_tickets: bool
    sale_paused: bool
    cloned_from_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    @classmethod
    def from_event(cls, event: Event) -> "EventRead":
        return cls(
            id=event.id,
            title=event.title,
            description=event.description,
            starts_at=event.starts_at,
            duration_min=event.duration_min,
            age_rating=event.age_rating,
            venue=event.venue,
            price=event.price,
            status=event.status,
            banner_small_url=event.banner_small_url,
            banner_large_url=event.banner_large_url,
            show_free_tickets=event.show_free_tickets,
            sale_paused=event.sale_paused,
            cloned_from_id=event.cloned_from_id,
            created_at=event.created_at,
            updated_at=event.updated_at,
            deleted_at=event.deleted_at,
        )


class TicketTypeSeed(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    price: Decimal = Field(ge=0)
    quota: int = Field(ge=0)


class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    description: str | None = None
    starts_at: datetime
    duration_min: int | None = Field(default=None, ge=0)
    age_rating: str | None = Field(default=None, max_length=16)
    venue: str | None = Field(default=None, max_length=512)
    banner_small_url: str | None = Field(default=None, max_length=1024)
    banner_large_url: str | None = Field(default=None, max_length=1024)
    show_free_tickets: bool = False
    sale_paused: bool = False
    ticket_types: list[TicketTypeSeed] | None = None


class EventUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=512)
    description: str | None = None
    starts_at: datetime | None = None
    duration_min: int | None = Field(default=None, ge=0)
    age_rating: str | None = Field(default=None, max_length=16)
    venue: str | None = Field(default=None, max_length=512)
    banner_small_url: str | None = Field(default=None, max_length=1024)
    banner_large_url: str | None = Field(default=None, max_length=1024)
    show_free_tickets: bool | None = None
    sale_paused: bool | None = None


class TicketTypeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    price: Decimal = Field(ge=0)
    quota: int = Field(ge=0)


class TicketTypeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    price: Decimal | None = Field(default=None, ge=0)
    quota: int | None = Field(default=None, ge=0)


class EventMove(BaseModel):
    starts_at: datetime


class EventListResponse(BaseModel):
    items: list[EventRead]
    total: int


class TicketTypeListResponse(BaseModel):
    items: list[TicketTypeRead]
