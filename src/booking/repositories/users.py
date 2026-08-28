from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from booking.models.users import Role, RoleCode, SystemUser
from booking.repositories.base import BaseRepository


class SystemUserRepository(BaseRepository[SystemUser]):
    model = SystemUser

    def _with_role(self) -> Any:
        return joinedload(SystemUser.role)

    async def get(self, entity_id: Any, **kwargs: Any) -> SystemUser | None:
        stmt = (
            select(SystemUser)
            .where(SystemUser.id == entity_id, SystemUser.deleted_at.is_(None))
            .options(self._with_role())
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(
        self, *, limit: int = 50, offset: int = 0
    ) -> tuple[Sequence[SystemUser], int]:
        stmt = (
            select(SystemUser)
            .where(SystemUser.deleted_at.is_(None))
            .options(self._with_role())
            .limit(limit)
            .offset(offset)
        )
        items = (await self._session.execute(stmt)).scalars().all()
        total_stmt = (
            select(func.count())
            .select_from(SystemUser)
            .where(SystemUser.deleted_at.is_(None))
        )
        total: int = (await self._session.execute(total_stmt)).scalar_one()
        return items, total

    async def get_by_email(self, email: str) -> SystemUser | None:
        stmt = self._base_select().where(SystemUser.email == email)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()


class RoleRepository(BaseRepository[Role]):
    model = Role

    async def get_by_code(self, code: RoleCode) -> Role | None:
        stmt = self._base_select().where(Role.code == code)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
