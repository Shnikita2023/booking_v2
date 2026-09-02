"""Discount schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from booking.models.discounts import Discount


class DiscountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    percent: int = Field(ge=1, le=100)
    discount_type: str = Field(default="global", pattern="^(global|event|client)$")
    event_id: uuid.UUID | None = None
    client_id: uuid.UUID | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    is_active: bool = True


class DiscountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    percent: int | None = Field(default=None, ge=1, le=100)
    is_active: bool | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None


class DiscountRead(BaseModel):
    id: uuid.UUID
    name: str
    percent: int
    discount_type: str
    event_id: uuid.UUID | None = None
    client_id: uuid.UUID | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    is_active: bool
    created_at: datetime

    @classmethod
    def from_discount(cls, discount: Discount) -> "DiscountRead":
        dt = discount.discount_type
        return cls(
            id=discount.id,
            name=discount.name,
            percent=discount.percent,
            discount_type=dt.value if hasattr(dt, "value") else str(dt),
            event_id=discount.event_id,
            client_id=discount.client_id,
            valid_from=discount.valid_from,
            valid_until=discount.valid_until,
            is_active=discount.is_active,
            created_at=discount.created_at,
        )


class DiscountListResponse(BaseModel):
    items: list[DiscountRead]
    total: int
