import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from booking.models.users import Role, RoleCode
from booking.repositories.users import RoleRepository, SystemUserRepository
from booking.services import security


@pytest_asyncio.fixture
async def admin_role(web_session: AsyncSession) -> Role:
    role = Role(code=RoleCode.ADMIN, name="Administrator")
    web_session.add(role)
    await web_session.flush()
    return role


@pytest_asyncio.fixture
async def staff_user(
    web_session: AsyncSession, admin_role: Role
) -> dict[str, str]:
    repo = SystemUserRepository(web_session)
    user = await repo.create(
        email="staff@example.com",
        password_hash=security.hash_password("staffpass123"),
        role_id=admin_role.id,
    )
    await web_session.commit()
    return {"id": str(user.id), "email": user.email}


@pytest_asyncio.fixture
async def role_repo(db_session: AsyncSession) -> RoleRepository:
    return RoleRepository(db_session)
