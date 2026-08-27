"""Client and staff authentication, registration and session management."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from booking.core.dto import Principal, TokenPair
from booking.core.errors import AppError
from booking.models.clients import Client, UserType
from booking.models.users import RoleCode, SystemUser
from booking.repositories.clients import ClientRepository
from booking.repositories.tokens import RefreshTokenRepository
from booking.repositories.users import RoleRepository, SystemUserRepository
from booking.services import security

MAX_FAILED_ATTEMPTS = 3
LOCK_MINUTES = 30


def _ensure_utc(value: datetime | None) -> datetime | None:
    """Normalize DB-provided datetime to timezone-aware UTC."""
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=UTC)


def _extract_jti(refresh_token: str) -> uuid.UUID:
    payload = security.decode_token(refresh_token, "refresh")
    if payload is None:
        raise AppError("Invalid token", code="invalid_token", status_code=401)
    return uuid.UUID(payload["jti"])


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._clients = ClientRepository(session)
        self._staff = SystemUserRepository(session)
        self._roles = RoleRepository(session)
        self._tokens = RefreshTokenRepository(session)

    async def register_client(
        self,
        *,
        email: str,
        password: str,
        full_name: str | None = None,
        phone: str | None = None,
    ) -> Client:
        if await self._clients.get_by_email(email) is not None:
            raise AppError(
                "Email already registered", code="email_taken", status_code=409
            )
        client = await self._clients.create(
            email=email,
            password_hash=security.hash_password(password),
            full_name=full_name,
            phone=phone,
            discount_percent=0,
        )
        await self._session.commit()
        return client

    async def client_login(self, *, email: str, password: str) -> TokenPair:
        client = await self._clients.get_by_email(email)
        self._ensure_not_locked(client.locked_until if client else None)
        valid = client is not None and security.verify_password(
            password, client.password_hash
        )
        if not valid or client is None:
            await self._register_failure(client)
            raise _login_failure_result(client)
        client.failed_attempts = 0
        pair = await self._issue_pair(UserType.CLIENT, client.id)
        await self._session.commit()
        return pair

    async def staff_login(self, *, email: str, password: str) -> TokenPair:
        staff = await self._staff.get_by_email(email)
        self._ensure_not_locked(staff.locked_until if staff else None)
        valid = (
            staff is not None
            and staff.is_active
            and security.verify_password(password, staff.password_hash)
        )
        if not valid or staff is None:
            await self._register_failure(staff)
            raise _login_failure_result(staff)
        staff.failed_attempts = 0
        await self._tokens.revoke_all_for_user(UserType.SYSTEM_USER, staff.id)
        pair = await self._issue_pair(UserType.SYSTEM_USER, staff.id)
        await self._session.commit()
        return pair

    async def refresh(self, refresh_token: str) -> TokenPair:
        payload = security.decode_token(refresh_token, "refresh")
        stored = (
            await self._tokens.get_active_by_jti(payload["jti"])
            if payload is not None
            else None
        )
        if payload is None or stored is None:
            raise AppError("Invalid token", code="invalid_token", status_code=401)
        user_type = UserType(payload["ut"])
        user_id = uuid.UUID(payload["sub"])
        if user_type == UserType.SYSTEM_USER and await self._get_role(user_id) is None:
            raise AppError("Invalid token", code="invalid_token", status_code=401)
        await self._tokens.revoke(stored)
        pair = await self._issue_pair(user_type, user_id)
        await self._session.commit()
        return pair

    async def logout(self, principal: Principal) -> None:
        await self._tokens.revoke_all_for_user(principal.user_type, principal.user_id)
        await self._session.commit()

    async def _issue_pair(self, user_type: UserType, user_id: uuid.UUID) -> TokenPair:
        extra: dict[str, str] = {"ut": user_type.value}
        role_claim = (
            await self._get_role(user_id) if user_type == UserType.SYSTEM_USER else None
        )
        if role_claim is not None:
            extra["role"] = role_claim.value
        subject = str(user_id)
        access, _ = security.create_token("access", subject, extra_claims=extra)
        refresh, expires_at = security.create_token(
            "refresh", subject, extra_claims=extra
        )
        await self._tokens.create(
            user_type=user_type,
            user_id=user_id,
            jti=_extract_jti(refresh),
            expires_at=expires_at,
        )
        return TokenPair(access_token=access, refresh_token=refresh)

    async def _get_role(self, user_id: uuid.UUID) -> RoleCode | None:
        staff = await self._staff.get(user_id)
        if staff is None:
            return None
        role = await self._roles.get(staff.role_id)
        return role.code if role else None

    @staticmethod
    def _ensure_not_locked(locked_until: datetime | None) -> None:
        locked_until = _ensure_utc(locked_until)
        now = datetime.now(UTC)
        if locked_until is not None and locked_until > now:
            retry_after = int((locked_until - now).total_seconds())
            raise AppError(
                f"Account locked, retry after {retry_after}s",
                code="account_locked",
                status_code=403,
            )

    async def _register_failure(self, user: Client | SystemUser | None) -> None:
        if user is None:
            return
        user.failed_attempts += 1
        if user.failed_attempts >= MAX_FAILED_ATTEMPTS:
            user.locked_until = datetime.now(UTC) + timedelta(minutes=LOCK_MINUTES)
        await self._session.commit()


def _login_failure_result(user: Client | SystemUser | None) -> AppError:
    """403 if the failed attempt triggered lockout, else generic 401."""
    now = datetime.now(UTC)
    locked_until = _ensure_utc(user.locked_until if user else None)
    if locked_until is not None and locked_until > now:
        retry_after = int((locked_until - now).total_seconds())
        return AppError(
            f"Account locked, retry after {retry_after}s",
            code="account_locked",
            status_code=403,
        )
    return AppError(
        "Invalid credentials", code="invalid_credentials", status_code=401
    )
