"""Admin management of client accounts."""

import uuid
from collections.abc import Sequence
from typing import Any

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from booking.core.errors import AppError
from booking.models.clients import Client
from booking.repositories.clients import ClientRepository
from booking.services import security


class ClientAdminService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._clients = ClientRepository(session)

    async def create(
        self,
        *,
        email: str,
        full_name: str | None,
        phone: str | None,
        password: str,
        discount_percent: int = 0,
    ) -> Client:
        existing = await self._clients.get_by_email(email)
        if existing is not None:
            raise AppError(
                "Email already registered", code="email_taken", status_code=status.HTTP_409_CONFLICT
            )
        client = await self._clients.create(
            email=email,
            full_name=full_name,
            phone=phone,
            password_hash=security.hash_password(password),
            is_active=True,
            discount_percent=discount_percent,
        )
        await self._session.commit()
        return client

    async def get(self, client_id: uuid.UUID) -> Client:
        client = await self._clients.get(client_id)
        if client is None:
            raise AppError(
                "Client not found",
                code="client_not_found",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return client

    async def list_all(
        self, *, limit: int = 50, offset: int = 0
    ) -> tuple[Sequence[Client], int]:
        return await self._clients.list_all(limit=limit, offset=offset)

    async def update(self, client_id: uuid.UUID, **changes: Any) -> Client:
        client = await self.get(client_id)
        await self._clients.update(client, **changes)
        await self._session.commit()
        return client

    async def reset_password(self, client_id: uuid.UUID, new_password: str) -> Client:
        client = await self.get(client_id)
        await self._clients.update(client, password_hash=security.hash_password(new_password))
        await self._session.commit()
        return client

    async def block(self, client_id: uuid.UUID) -> Client:
        client = await self.get(client_id)
        await self._clients.update(client, is_active=False)
        await self._session.commit()
        return client

    async def unblock(self, client_id: uuid.UUID) -> Client:
        client = await self.get(client_id)
        await self._clients.update(client, is_active=True)
        await self._session.commit()
        return client

    async def delete(self, client_id: uuid.UUID) -> None:
        await self.get(client_id)
        await self._clients.soft_delete(client_id)
        await self._session.commit()
