from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.community.postgres import PostgresContainer

from booking.db.engine import get_engine, get_session
from booking.main import app
from booking.models import Base

pytest_plugins = ["tests.factories"]


@pytest.fixture(scope="session")
def pg_container() -> Generator[PostgresContainer, None, None]:
    with PostgresContainer("postgres:16-alpine") as container:
        yield container


@pytest_asyncio.fixture(scope="session")
async def pg_engine(pg_container: PostgresContainer) -> AsyncGenerator[AsyncEngine, None]:
    url = pg_container.get_connection_url(driver="asyncpg")
    engine = create_async_engine(url)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_schema(pg_engine: AsyncEngine) -> AsyncGenerator[None, None]:
    """Fresh schema (real Postgres) for every test."""
    async with pg_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with pg_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(
    db_schema: None, pg_engine: AsyncEngine
) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(pg_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def web_session(
    db_schema: None, pg_engine: AsyncEngine
) -> AsyncGenerator[AsyncSession, None]:
    """Session into the same DB the app under test uses."""
    factory = async_sessionmaker(pg_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(
    db_schema: None, pg_engine: AsyncEngine
) -> AsyncGenerator[AsyncClient, None]:
    session_factory = async_sessionmaker(pg_engine, expire_on_commit=False)

    async def override_engine() -> object:
        return pg_engine

    async def override_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_engine] = override_engine
    app.dependency_overrides[get_session] = override_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
