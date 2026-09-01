"""Client profile endpoints (C-5): view and update profile."""

from fastapi import APIRouter, status

from booking.core.deps import ClientPrincipal, SessionDep
from booking.core.errors import AppError
from booking.repositories.clients import ClientRepository
from booking.schemas.auth import MeResponse
from booking.schemas.client_profile import ProfileUpdateRequest

router = APIRouter(prefix="/api/v1/client", tags=["client-profile"])


@router.get(
    "/profile",
    summary="Get my profile",
    description="Return the authenticated client's profile.",
    response_model=MeResponse,
)
async def get_profile(
    principal: ClientPrincipal,
    session: SessionDep,
) -> MeResponse:
    client = await ClientRepository(session).get(principal.user_id)
    if client is None:
        raise AppError(
            "Client not found", code="client_not_found", status_code=status.HTTP_404_NOT_FOUND
        )
    return MeResponse(
        id=client.id,
        email=client.email,
        user_type="client",
        full_name=client.full_name,
        discount_percent=client.discount_percent,
    )


@router.put(
    "/profile",
    summary="Update my profile",
    description="Update the authenticated client's profile (name, phone).",
    response_model=MeResponse,
)
async def update_profile(
    body: ProfileUpdateRequest,
    principal: ClientPrincipal,
    session: SessionDep,
) -> MeResponse:
    repo = ClientRepository(session)
    client = await repo.get(principal.user_id)
    if client is None:
        raise AppError(
            "Client not found", code="client_not_found", status_code=status.HTTP_404_NOT_FOUND
        )
    updates = body.model_dump(exclude_unset=True)
    client = await repo.update(client, **updates)
    return MeResponse(
        id=client.id,
        email=client.email,
        user_type="client",
        full_name=client.full_name,
        discount_percent=client.discount_percent,
    )
