"""Admin schemas for client accounts."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from booking.models.clients import Client


class ClientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str | None = None
    phone: str | None = None
    is_active: bool
    discount_percent: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    @classmethod
    def from_client(cls, client: Client) -> "ClientRead":
        return cls(
            id=client.id,
            email=client.email,
            full_name=client.full_name,
            phone=client.phone,
            is_active=client.is_active,
            discount_percent=client.discount_percent,
            created_at=client.created_at,
            updated_at=client.updated_at,
            deleted_at=client.deleted_at,
        )


class ClientCreate(BaseModel):
    email: EmailStr = Field(min_length=3, max_length=255)
    full_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    password: str = Field(min_length=8, max_length=128)
    discount_percent: int = Field(default=0, ge=0, le=100)


class ClientUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    discount_percent: int | None = Field(default=None, ge=0, le=100)


class PasswordReset(BaseModel):
    password: str = Field(min_length=8, max_length=128)


class ClientListResponse(BaseModel):
    items: list[ClientRead]
    total: int
