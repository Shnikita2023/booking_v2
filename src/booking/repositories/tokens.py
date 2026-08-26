import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from booking.models.clients import RefreshToken, UserType
from booking.repositories.base import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshToken

    async def get_active_by_jti(self, jti: str) -> RefreshToken | None:
        try:
            jti_uuid = uuid.UUID(jti)
        except ValueError:
            return None
        stmt = self._base_select().where(
            RefreshToken.jti == jti_uuid,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(UTC),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke(self, token: RefreshToken) -> None:
        token.revoked_at = datetime.now(UTC)
        await self._session.flush()

    async def revoke_all_for_user(
        self, user_type: UserType, user_id: uuid.UUID
    ) -> int:
        """Revoke all active tokens; returns count. Used by single-session rule."""
        stmt = select(RefreshToken).where(
            RefreshToken.user_type == user_type,
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
        tokens = (await self._session.execute(stmt)).scalars().all()
        now = datetime.now(UTC)
        for token in tokens:
            token.revoked_at = now
        await self._session.flush()
        return len(tokens)

