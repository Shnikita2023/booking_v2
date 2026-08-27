"""Staff (system personnel) authentication endpoints."""

from dataclasses import asdict

from fastapi import APIRouter

from booking.core.deps import SessionDep
from booking.schemas.auth import LoginRequest, TokenResponse
from booking.services.auth_service import AuthService

router = APIRouter(prefix="/api/v1/staff", tags=["staff"])


@router.post(
    "/login",
    summary="Staff login",
    description="Authenticate system personnel and issue access/refresh JWT tokens.",
    response_model=TokenResponse,
)
async def login(body: LoginRequest, session: SessionDep) -> TokenResponse:
    pair = await AuthService(session).staff_login(
        email=body.email, password=body.password
    )
    return TokenResponse(**asdict(pair))
