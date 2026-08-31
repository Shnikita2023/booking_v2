"""Admin management of system (staff) users."""

import uuid
from collections.abc import Sequence
from typing import Any

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from booking.core.dto import Principal
from booking.core.errors import AppError
from booking.models.audit import AuditAction
from booking.models.users import Role, RoleCode, SystemUser
from booking.repositories.users import RoleRepository, SystemUserRepository
from booking.services import security
from booking.services.audit_service import AuditService


class SystemUserAdminService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = SystemUserRepository(session)
        self._roles = RoleRepository(session)
        self._audit = AuditService(session)

    async def _ensure_role(self, role_code: RoleCode) -> Role:
        role = await self._roles.get_by_code(role_code)
        if role is None:
            role = Role(code=role_code, name=role_code.value.title())
            self._session.add(role)
            await self._session.flush()
        return role

    async def create(
        self, *, email: str, password: str, role_code: RoleCode, actor: Principal | None = None
    ) -> SystemUser:
        role = await self._ensure_role(role_code)
        existing = await self._users.get_by_email(email)
        if existing is not None:
            raise AppError(
                "Email already registered", code="email_taken", status_code=status.HTTP_409_CONFLICT
            )
        user = await self._users.create(
            email=email,
            password_hash=security.hash_password(password),
            role_id=role.id,
            is_active=True,
        )
        await self._audit.record(
            action=AuditAction.USER_CREATE,
            entity_type="system_user",
            entity_id=user.id,
            actor=actor,
            payload={"email": email, "role": role_code.value},
        )
        await self._session.commit()
        return await self.get(user.id)

    async def get(self, user_id: uuid.UUID) -> SystemUser:
        user = await self._users.get(user_id)
        if user is None:
            raise AppError(
                "System user not found",
                code="user_not_found",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return user

    async def list_all(
        self, *, limit: int = 50, offset: int = 0
    ) -> tuple[Sequence[SystemUser], int]:
        return await self._users.list_all(limit=limit, offset=offset)

    async def update(
        self, user_id: uuid.UUID, *, actor: Principal | None = None, **changes: Any
    ) -> SystemUser:
        user = await self.get(user_id)
        role_code = changes.pop("role_code", None)
        if role_code is not None:
            role = await self._ensure_role(role_code)
            changes["role_id"] = role.id
        await self._users.update(user, **changes)
        await self._audit.record(
            action=AuditAction.USER_UPDATE,
            entity_type="system_user",
            entity_id=user_id,
            actor=actor,
            payload=changes,
        )
        await self._session.commit()
        await self._session.refresh(user, ["role"])
        return user

    async def reset_password(
        self, user_id: uuid.UUID, new_password: str, *, actor: Principal | None = None
    ) -> SystemUser:
        user = await self.get(user_id)
        await self._users.update(user, password_hash=security.hash_password(new_password))
        await self._audit.record(
            action=AuditAction.USER_RESET_PASSWORD,
            entity_type="system_user",
            entity_id=user_id,
            actor=actor,
        )
        await self._session.commit()
        return user

    async def block(self, user_id: uuid.UUID, *, actor: Principal | None = None) -> SystemUser:
        user = await self.get(user_id)
        await self._users.update(user, is_active=False)
        await self._audit.record(
            action=AuditAction.USER_BLOCK,
            entity_type="system_user",
            entity_id=user_id,
            actor=actor,
            payload={"is_active": False},
        )
        await self._session.commit()
        return user

    async def unblock(self, user_id: uuid.UUID, *, actor: Principal | None = None) -> SystemUser:
        user = await self.get(user_id)
        await self._users.update(user, is_active=True)
        await self._audit.record(
            action=AuditAction.USER_UNBLOCK,
            entity_type="system_user",
            entity_id=user_id,
            actor=actor,
            payload={"is_active": True},
        )
        await self._session.commit()
        return user

    async def delete(self, user_id: uuid.UUID, *, actor: Principal | None = None) -> None:
        await self.get(user_id)
        await self._users.soft_delete(user_id)
        await self._audit.record(
            action=AuditAction.USER_DELETE,
            entity_type="system_user",
            entity_id=user_id,
            actor=actor,
        )
        await self._session.commit()
