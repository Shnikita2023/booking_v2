import uuid
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from booking.models.clients import Client
from booking.models.users import Role, RoleCode, SystemUser
from booking.repositories.base import BaseRepository


class SystemUserRepository(BaseRepository[SystemUser]):
    model = SystemUser


class ClientRepository(BaseRepository[Client]):
    model = Client


@pytest.fixture
async def admin_role(db_session: AsyncSession) -> Role:
    role = Role(code=RoleCode.ADMIN, name="Administrator")
    db_session.add(role)
    await db_session.flush()
    return role


@pytest.fixture
async def user_repo(db_session: AsyncSession) -> AsyncGenerator[SystemUserRepository, None]:
    yield SystemUserRepository(db_session)


async def test_create_and_get(user_repo: SystemUserRepository, admin_role: Role) -> None:
    user = await user_repo.create(
        email="admin@example.com", password_hash="hash", role_id=admin_role.id
    )
    assert user.id is not None
    fetched = await user_repo.get(user.id)
    assert fetched is not None
    assert fetched.email == "admin@example.com"


async def test_soft_delete_filters_reads(
    user_repo: SystemUserRepository, admin_role: Role
) -> None:
    user = await user_repo.create(
        email="gone@example.com", password_hash="h", role_id=admin_role.id
    )
    assert await user_repo.soft_delete(user.id) is True
    assert await user_repo.get(user.id) is None
    assert await user_repo.list() == []
    assert await user_repo.soft_delete(uuid.uuid4()) is False


async def test_update_bumps_version(
    db_session: AsyncSession, admin_role: Role
) -> None:
    client = Client(
        email="c@example.com", password_hash="h", discount_percent=0
    )
    db_session.add(client)
    await db_session.flush()
    repo = ClientRepository(db_session)

    assert client.version == 1
    await repo.update(client, discount_percent=15)
    assert client.version == 2
    assert client.discount_percent == 15
