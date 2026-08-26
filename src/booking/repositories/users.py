from booking.models.users import Role, RoleCode, SystemUser
from booking.repositories.base import BaseRepository


class SystemUserRepository(BaseRepository[SystemUser]):
    model = SystemUser

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
