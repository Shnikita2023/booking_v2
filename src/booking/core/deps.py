import uuid
from typing import Annotated, Any

import jwt as pyjwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from booking.core.errors import AppError
from booking.db.engine import get_session
from booking.models.clients import Client, UserType
from booking.models.users import RoleCode
from booking.repositories.clients import ClientRepository
from booking.repositories.users import RoleRepository, SystemUserRepository
from booking.services import security
from booking.services.auth_service import Principal

_bearer = HTTPBearer(auto_error=False)

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _decode_access(token: str) -> dict[str, Any]:
    payload = security.decode_token(token, "access")
    if payload is None:
        raise AppError("Invalid token", code="invalid_token", status_code=401)
    return payload


async def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> Principal:
    if credentials is None:
        raise AppError("Not authenticated", code="not_authenticated", status_code=401)
    try:
        payload = _decode_access(credentials.credentials)
        user_type = UserType(payload["ut"])
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError, pyjwt.PyJWTError) as exc:
        raise AppError("Invalid token", code="invalid_token", status_code=401) from exc

    role: RoleCode | None = None
    raw_role = payload.get("role")
    if user_type == UserType.SYSTEM_USER:
        staff = await SystemUserRepository(session).get(user_id)
        if staff is None or not staff.is_active:
            raise AppError("Invalid token", code="invalid_token", status_code=401)
        role_entity = await RoleRepository(session).get(staff.role_id)
        role = role_entity.code if role_entity else None
    elif raw_role is not None:
        raise AppError("Invalid token", code="invalid_token", status_code=401)
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

    async def dependency(principal: Principal) -> Principal:
        if principal.user_type != UserType.SYSTEM_USER or principal.role not in allowed:
            raise AppError("Forbidden", code="forbidden", status_code=403)
        return principal

    return dependency
