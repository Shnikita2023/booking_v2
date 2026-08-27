from dataclasses import asdict

from fastapi import APIRouter, status
from sqlalchemy.ext.asyncio import AsyncSession

from booking.core.deps import CurrentPrincipal, SessionDep
from booking.core.errors import AppError
from booking.dto import Principal
from booking.models.clients import Client, UserType
from booking.models.users import SystemUser
from booking.repositories.clients import ClientRepository
from booking.repositories.users import SystemUserRepository
from booking.schemas.auth import (
    LoginRequest,
    MeResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from booking.services.auth_service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, session: SessionDep) -> dict[str, str]:
    service = AuthService(session)
    client = await service.register_client(
        email=body.email,
        password=body.password,
        full_name=body.full_name,
        phone=body.phone,
    )
    return {"id": str(client.id), "email": client.email}


async def _me_payload(principal: Principal, session: AsyncSession) -> MeResponse:
    if principal.user_type == UserType.CLIENT:
        client: Client | None = await ClientRepository(session).get(principal.user_id)
        if client is None:
            raise AppError("Invalid token", code="invalid_token", status_code=401)
        return MeResponse(
            id=client.id,
            email=client.email,
            user_type="client",
            full_name=client.full_name,
            discount_percent=client.discount_percent,
        )
    staff: SystemUser | None = await SystemUserRepository(session).get(
        principal.user_id
    )
    if staff is None:
        raise AppError("Invalid token", code="invalid_token", status_code=401)
    return MeResponse(
        id=staff.id,
        email=staff.email,
        user_type="system_user",
        role=None if principal.role is None else principal.role.value,
    )


@router.get("/me")
async def me(
    principal: CurrentPrincipal, session: SessionDep
) -> MeResponse:
    return await _me_payload(principal, session)


@router.post("/login")
async def login(body: LoginRequest, session: SessionDep) -> TokenResponse:
    pair = await AuthService(session).client_login(
        email=body.email, password=body.password
    )
    return TokenResponse(**asdict(pair))


@router.post("/refresh")
async def refresh(body: RefreshRequest, session: SessionDep) -> TokenResponse:
    pair = await AuthService(session).refresh(body.refresh_token)
    return TokenResponse(**asdict(pair))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    principal: CurrentPrincipal, session: SessionDep
) -> None:
    await AuthService(session).logout(principal)
