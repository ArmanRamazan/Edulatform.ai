from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header
from fastapi.responses import Response

from common.errors import AppError
from app.domain.user import PublicProfileResponse, VisibilityUpdate
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/users", tags=["profiles"])


def _get_profile_service() -> ProfileService:
    from app.main import get_profile_service
    return get_profile_service()


def _get_current_user_id(authorization: Annotated[str, Header()]) -> UUID:
    from app.main import app_settings

    if not authorization.startswith("Bearer "):
        raise AppError("Invalid authorization header", status_code=401)
    token = authorization[7:]
    try:
        payload = jwt.decode(
            token, app_settings.jwt_secret, algorithms=[app_settings.jwt_algorithm]
        )
        return UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise AppError("Invalid token", status_code=401) from exc


@router.get("/{user_id}/profile", response_model=PublicProfileResponse)
async def get_public_profile(
    user_id: UUID,
    service: Annotated[ProfileService, Depends(_get_profile_service)],
) -> PublicProfileResponse:
    profile = await service.get_public_profile(user_id)
    return PublicProfileResponse(
        id=profile.id,
        name=profile.name,
        bio=profile.bio,
        avatar_url=profile.avatar_url,
        role=profile.role,
        is_verified=profile.is_verified,
        created_at=profile.created_at,
        is_public=profile.is_public,
    )


@router.get("/{user_id}/stats")
async def get_user_stats(
    user_id: UUID,
    service: Annotated[ProfileService, Depends(_get_profile_service)],
) -> dict:
    return await service.get_user_stats(user_id)


@router.patch("/me/visibility", status_code=204)
async def update_visibility(
    body: VisibilityUpdate,
    user_id: Annotated[UUID, Depends(_get_current_user_id)],
    service: Annotated[ProfileService, Depends(_get_profile_service)],
) -> Response:
    await service.update_visibility(user_id, body.is_public)
    return Response(status_code=204)
