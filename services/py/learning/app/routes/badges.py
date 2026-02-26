from __future__ import annotations

from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header

from common.errors import AppError
from app.domain.badge import BadgeListResponse
from app.services.badge_service import BadgeService

router = APIRouter(prefix="/badges", tags=["badges"])


def _get_badge_service() -> BadgeService:
    from app.main import get_badge_service
    return get_badge_service()


def _get_current_user_claims(authorization: Annotated[str, Header()]) -> dict:
    from app.main import app_settings

    if not authorization.startswith("Bearer "):
        raise AppError("Invalid authorization header", status_code=401)
    token = authorization[7:]
    try:
        payload = jwt.decode(
            token, app_settings.jwt_secret, algorithms=[app_settings.jwt_algorithm]
        )
        return {
            "user_id": UUID(payload["sub"]),
            "role": payload.get("role", "student"),
            "is_verified": payload.get("is_verified", False),
        }
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise AppError("Invalid token", status_code=401) from exc


@router.get("/me", response_model=BadgeListResponse)
async def get_my_badges(
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[BadgeService, Depends(_get_badge_service)],
) -> BadgeListResponse:
    return await service.get_badges(user_id=claims["user_id"])
