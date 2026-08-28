"""Dependency wiring: sessions, authentication and RBAC."""

import uuid
from typing import Annotated, Any

import jwt as pyjwt
from fastapi import Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from booking.core.dto import Principal
from booking.core.errors import AppError
from booking.db.engine import get_session
from booking.models.clients import Client, UserType
from booking.models.users import RoleCode
from booking.repositories.clients import ClientRepository
from booking.repositories.users import RoleRepository, SystemUserRepository
from booking.services import security

_bearer = HTTPBearer(auto_error=False)

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _decode_access(token: str) -> dict[str, Any]:
    payload = security.decode_token(token, "access")
    if payload is None:
        raise AppError(
            "Invalid token", code="invalid_token", status_code=status.HTTP_401_UNAUTHORIZED
        )
    return payload


async def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> Principal:
    if credentials is None:
        raise AppError(
            "Not authenticated", code="not_authenticated", status_code=status.HTTP_401_UNAUTHORIZED
        )
    try:
        payload = _decode_access(credentials.credentials)
        user_type = UserType(payload["ut"])
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError, pyjwt.PyJWTError) as exc:
        raise AppError(
            "Invalid token", code="invalid_token", status_code=status.HTTP_401_UNAUTHORIZED
        ) from exc

    role: RoleCode | None = None
    raw_role = payload.get("role")
    if user_type == UserType.SYSTEM_USER:
        staff = await SystemUserRepository(session).get(user_id)
        if staff is None or not staff.is_active:
            raise AppError(
                "Invalid token", code="invalid_token", status_code=status.HTTP_401_UNAUTHORIZED
            )
        role_entity = await RoleRepository(session).get(staff.role_id)
        role = role_entity.code if role_entity else None
    elif raw_role is not None:
        raise AppError(
            "Invalid token", code="invalid_token", status_code=status.HTTP_401_UNAUTHORIZED
        )
    return Principal(user_type=user_type, user_id=user_id, role=role)


CurrentPrincipal = Annotated[Principal, Depends(get_current_principal)]


async def get_optional_client(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> Client | None:
    if principal.user_type != UserType.CLIENT:
        return None
    return await ClientRepository(session).get(principal.user_id)


def require_role(*allowed: RoleCode) -> Any:
    """Dependency factory; use as `Annotated[Principal, Depends(require_role(...))]`."""

    async def dependency(principal: Principal = Depends(get_current_principal)) -> Principal:
        if principal.user_type != UserType.SYSTEM_USER or principal.role not in allowed:
            raise AppError("Forbidden", code="forbidden", status_code=status.HTTP_403_FORBIDDEN)
        return principal

    return dependency


async def require_client(principal: Principal = Depends(get_current_principal)) -> Principal:
    """Allow only authenticated clients; staff gets 403, anonymous 401."""
    if principal.user_type != UserType.CLIENT:
        raise AppError("Forbidden", code="forbidden", status_code=status.HTTP_403_FORBIDDEN)
    return principal


ClientPrincipal = Annotated[Principal, Depends(require_client)]

from booking.services.audit_service import AuditService  # noqa: E402
from booking.services.client_admin_service import ClientAdminService  # noqa: E402
from booking.services.event_admin_service import EventAdminService  # noqa: E402
from booking.services.settings_service import SettingsService  # noqa: E402
from booking.services.user_admin_service import SystemUserAdminService  # noqa: E402


def _event_admin_service(session: SessionDep) -> EventAdminService:
    return EventAdminService(session)


def _client_admin_service(session: SessionDep) -> ClientAdminService:
    return ClientAdminService(session)


def _system_user_admin_service(session: SessionDep) -> SystemUserAdminService:
    return SystemUserAdminService(session)


def _settings_service(session: SessionDep) -> SettingsService:
    return SettingsService(session)


def _audit_service(session: SessionDep) -> AuditService:
    return AuditService(session)


EventAdminServiceDep = Annotated[EventAdminService, Depends(_event_admin_service)]
ClientAdminServiceDep = Annotated[ClientAdminService, Depends(_client_admin_service)]
SystemUserAdminServiceDep = Annotated[SystemUserAdminService, Depends(_system_user_admin_service)]
SettingsServiceDep = Annotated[SettingsService, Depends(_settings_service)]
AuditServiceDep = Annotated[AuditService, Depends(_audit_service)]
