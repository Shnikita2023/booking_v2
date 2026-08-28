"""Admin read-only audit journal endpoint (S-7)."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from booking.core.deps import AuditServiceDep, require_role
from booking.core.dto import Principal
from booking.models.audit import AuditAction
from booking.models.clients import UserType
from booking.models.users import RoleCode
from booking.schemas.audit import AuditListResponse, AuditRead

AdminOnly = Annotated[Principal, Depends(require_role(RoleCode.ADMIN))]

router = APIRouter(prefix="/api/v1/admin/audit", tags=["admin:audit"])


@router.get(
    "",
    summary="List audit events",
    description="Read-only journal of system-user and client actions (S-7). "
    "Supports filtering by actor, action and entity, newest first.",
    response_model=AuditListResponse,
)
async def list_audit(
    service: AuditServiceDep,
    _principal: AdminOnly,
    action: AuditAction | None = Query(default=None),
    actor_type: UserType | None = Query(default=None),
    actor_id: uuid.UUID | None = Query(default=None),
    actor_role: RoleCode | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    entity_id: uuid.UUID | None = Query(default=None),
    from_at: datetime | None = Query(default=None),
    to_at: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> AuditListResponse:
    items, total = await service.search(
        action=action,
        actor_type=actor_type,
        actor_id=actor_id,
        actor_role=actor_role,
        entity_type=entity_type,
        entity_id=entity_id,
        from_at=from_at,
        to_at=to_at,
        limit=limit,
        offset=offset,
    )
    return AuditListResponse(items=[AuditRead.from_log(log) for log in items], total=total)
