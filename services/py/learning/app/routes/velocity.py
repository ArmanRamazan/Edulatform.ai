from __future__ import annotations

from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header

from common.errors import AppError
from app.domain.velocity import VelocityResponse
from app.services.velocity_service import VelocityService

router = APIRouter(prefix="/velocity", tags=["velocity"])


def _get_velocity_service() -> VelocityService:
    from app.main import get_velocity_service
    return get_velocity_service()


def _get_current_user_id(authorization: Annotated[str, Header()]) -> UUID:
    from app.main import app_settings

    if not authorization.startswith("Bearer "):
        raise AppError("Invalid authorization header", status_code=401)
    token = authorization[7:]
    try:
        payload = jwt.decode(
            token, app_settings.jwt_secret, algorithms=[app_settings.jwt_algorithm],
        )
        return UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise AppError("Invalid token", status_code=401) from exc


@router.get("/me", response_model=VelocityResponse)
async def get_my_velocity(
    user_id: Annotated[UUID, Depends(_get_current_user_id)],
    service: Annotated[VelocityService, Depends(_get_velocity_service)],
) -> dict:
    return await service.get_velocity(user_id)
