"""Admin schemas for system (staff) users."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from booking.models.users import RoleCode, SystemUser


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str | None = None
    role_code: RoleCode
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    @classmethod
    def from_user(cls, user: SystemUser) -> "UserRead":
        return cls(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role_code=user.role.code,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
            deleted_at=user.deleted_at,
        )


class UserCreate(BaseModel):
    email: EmailStr = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    role_code: RoleCode


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    role_code: RoleCode | None = None
    is_active: bool | None = None


class PasswordReset(BaseModel):
    password: str = Field(min_length=8, max_length=128)


class UserListResponse(BaseModel):
    items: list[UserRead]
    total: int
