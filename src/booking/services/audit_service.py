"""Audit journal service: record actions and query the read-only journal (S-7)."""

import datetime
import enum
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from booking.core.dto import Principal
from booking.models.audit import AuditAction, AuditLog
from booking.models.clients import UserType
from booking.repositories.audit import AuditRepository


def _json_safe(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime.datetime):
        return value.isoformat()
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = AuditRepository(session)

    async def record(
        self,
        *,
        action: AuditAction,
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
        actor: Principal | None = None,
        payload: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Append an audit entry. Actor identity is taken from ``actor`` (may be None)."""
        actor_role = (
            actor.role
            if actor is not None and actor.user_type == UserType.SYSTEM_USER
            else None
        )
        record = AuditLog(
            actor_type=actor.user_type if actor is not None else None,
            actor_id=actor.user_id if actor is not None else None,
            actor_role=actor_role,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=_json_safe(payload),
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def search(self, **filters: Any) -> tuple[list[AuditLog], int]:
        return await self._repo.search(**filters)
