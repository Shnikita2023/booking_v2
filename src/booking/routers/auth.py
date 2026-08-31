"""Client and staff authentication endpoints."""

from dataclasses import asdict

from fastapi import APIRouter, status
from sqlalchemy.ext.asyncio import AsyncSession

from booking.core.deps import CurrentPrincipal, SessionDep
from booking.core.dto import Principal
from booking.core.errors import AppError
from booking.models.clients import Client, UserType
from booking.models.users import SystemUser
from booking.repositories.clients import ClientRepository
from booking.repositories.users import SystemUserRepository
from booking.schemas.auth import (
    LoginRequest,
    MeResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)
from booking.services.auth_service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Register a new client",
    description="Create a client account with email and password.",
    response_model=RegisterResponse,
)
async def register(body: RegisterRequest, session: SessionDep) -> RegisterResponse:
    service = AuthService(session)
    client = await service.register_client(
        email=body.email,
        password=body.password,
        full_name=body.full_name,
        phone=body.phone,
    )
    return RegisterResponse(id=str(client.id), email=client.email)


async def _me_payload(principal: Principal, session: AsyncSession) -> MeResponse:
    if principal.user_type == UserType.CLIENT:
        client: Client | None = await ClientRepository(session).get(principal.user_id)
        if client is None:
            raise AppError(
                "Invalid token", code="invalid_token", status_code=status.HTTP_401_UNAUTHORIZED
            )
        return MeResponse(
            id=client.id,
            email=client.email,
            user_type="client",
            full_name=client.full_name,
            discount_percent=client.discount_percent,
        )
    staff: SystemUser | None = await SystemUserRepository(session).get(principal.user_id)
    if staff is None:
        raise AppError(
            "Invalid token", code="invalid_token", status_code=status.HTTP_401_UNAUTHORIZED
        )
    return MeResponse(
        id=staff.id,
        email=staff.email,
        user_type="system_user",
        role=None if principal.role is None else principal.role.value,
    )


@router.get(
    "/me",
    summary="Current principal profile",
    description="Return the profile of the authenticated client or staff member.",
    response_model=MeResponse,
)
async def me(principal: CurrentPrincipal, session: SessionDep) -> MeResponse:
    return await _me_payload(principal, session)


@router.post(
    "/login",
    summary="Client login",
    description="Authenticate a client and issue access/refresh JWT tokens.",
    response_model=TokenResponse,
)
async def login(body: LoginRequest, session: SessionDep) -> TokenResponse:
    pair = await AuthService(session).client_login(email=body.email, password=body.password)
    return TokenResponse(**asdict(pair))


@router.post(
    "/refresh",
    summary="Refresh access token",
    description="Exchange a valid refresh token for a new access/refresh pair.",
    response_model=TokenResponse,
)
async def refresh(body: RefreshRequest, session: SessionDep) -> TokenResponse:
    pair = await AuthService(session).refresh(body.refresh_token)
    return TokenResponse(**asdict(pair))


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout",
    description="Revoke the current refresh token (single-session policy).",
    response_model=None,
)
async def logout(principal: CurrentPrincipal, session: SessionDep) -> None:
    await AuthService(session).logout(principal)
