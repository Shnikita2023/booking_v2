"""Admin schemas for the audit journal (S-7)."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from booking.models.audit import AuditAction, AuditLog
from booking.models.clients import UserType
from booking.models.users import RoleCode


class AuditRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor_type: UserType | None = None
    actor_id: UUID | None = None
    actor_role: RoleCode | None = None
    action: AuditAction
    entity_type: str | None = None
    entity_id: UUID | None = None
    payload: dict[str, Any] | None = None
    created_at: datetime

    @classmethod
    def from_log(cls, log: AuditLog) -> "AuditRead":
        return cls(
            id=log.id,
            actor_type=log.actor_type,
            actor_id=log.actor_id,
            actor_role=log.actor_role,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            payload=log.payload,
            created_at=log.created_at,
        )


class AuditListResponse(BaseModel):
    items: list[AuditRead]
    total: int
