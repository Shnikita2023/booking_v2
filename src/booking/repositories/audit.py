"""Repository for the append-only audit journal (no update/delete)."""

import uuid
from datetime import datetime

from sqlalchemy import func, select

from booking.models.audit import AuditAction, AuditLog
from booking.models.clients import UserType
from booking.models.users import RoleCode
from booking.repositories.base import BaseRepository


class AuditRepository(BaseRepository[AuditLog]):
    model = AuditLog

    async def search(
        self,
        *,
        actor_type: UserType | None = None,
        actor_id: uuid.UUID | None = None,
        actor_role: RoleCode | None = None,
        action: AuditAction | None = None,
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
        from_at: datetime | None = None,
        to_at: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        conditions = []
        if actor_type is not None:
            conditions.append(AuditLog.actor_type == actor_type)
        if actor_id is not None:
            conditions.append(AuditLog.actor_id == actor_id)
        if actor_role is not None:
            conditions.append(AuditLog.actor_role == actor_role)
        if action is not None:
            conditions.append(AuditLog.action == action)
        if entity_type is not None:
            conditions.append(AuditLog.entity_type == entity_type)
        if entity_id is not None:
            conditions.append(AuditLog.entity_id == entity_id)
        if from_at is not None:
            conditions.append(AuditLog.created_at >= from_at)
        if to_at is not None:
            conditions.append(AuditLog.created_at <= to_at)

        rows_stmt = select(AuditLog)
        count_stmt = select(func.count()).select_from(AuditLog)
        for condition in conditions:
            rows_stmt = rows_stmt.where(condition)
            count_stmt = count_stmt.where(condition)

        total = (await self._session.execute(count_stmt)).scalar_one()
        rows = (
            await self._session.execute(
                rows_stmt.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
            )
        ).scalars().all()
        return list(rows), total
