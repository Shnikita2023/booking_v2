import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import ColumnExpressionArgument, Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import InstrumentedAttribute

from booking.models.base import Base


class BaseRepository[ModelT: Base]:
    """Generic repository: data access only, no business logic.

    Soft-deleted rows are excluded from all reads by default.
    """

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _soft_delete_filter(self) -> ColumnExpressionArgument[bool] | None:
        deleted_at = getattr(self.model, "deleted_at", None)
        if isinstance(deleted_at, InstrumentedAttribute):
            return deleted_at.is_(None)
        return None

    def _base_select(self) -> Select[tuple[ModelT]]:
        stmt = select(self.model)
        condition = self._soft_delete_filter()
        if condition is not None:
            stmt = stmt.where(condition)
        return stmt

    async def get(self, entity_id: uuid.UUID) -> ModelT | None:
        id_field = "id"
        model_id = cast(
            "InstrumentedAttribute[uuid.UUID]", getattr(self.model, id_field)
        )
        stmt = self._base_select().where(model_id == entity_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(self, *, limit: int = 50, offset: int = 0) -> Sequence[ModelT]:
        stmt = self._base_select().limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def create(self, **data: Any) -> ModelT:
        entity = self.model(**data)
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def update(self, entity: ModelT, **data: Any) -> ModelT:
        for key, value in data.items():
            setattr(entity, key, value)
        version = getattr(entity, "version", None)
        if version is not None:
            version_field = "version"
            setattr(entity, version_field, version + 1)
        await self._session.flush()
        return entity

    async def soft_delete(self, entity_id: uuid.UUID) -> bool:
        entity = await self.get(entity_id)
        if entity is None:
            return False
        deleted_at = getattr(self.model, "deleted_at", None)
        if not isinstance(deleted_at, InstrumentedAttribute):
            return False
        deleted_field = "deleted_at"
        setattr(entity, deleted_field, datetime.now(UTC))
        await self._session.flush()
        return True
