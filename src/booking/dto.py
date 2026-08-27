import uuid
from dataclasses import dataclass

from booking.models.clients import UserType
from booking.models.users import RoleCode


@dataclass(slots=True)
class TokenPair:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


@dataclass(slots=True)
class Principal:
    user_type: UserType
    user_id: uuid.UUID
    role: RoleCode | None = None


@dataclass(slots=True)
class OrderItem:
    ticket_type_id: uuid.UUID
    quantity: int
