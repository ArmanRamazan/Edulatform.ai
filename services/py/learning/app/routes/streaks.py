from __future__ import annotations

from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header

from common.errors import AppError, ForbiddenError
from app.domain.streak import AtRiskResponse, StreakResponse
from app.services.streak_service import StreakService

router = APIRouter(prefix="/streaks", tags=["streaks"])


def _get_streak_service() -> StreakService:
    from app.main import get_streak_service
    return get_streak_service()


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


@router.post("/activity", response_model=StreakResponse)
async def record_activity(
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[StreakService, Depends(_get_streak_service)],
) -> StreakResponse:
    streak = await service.record_activity(user_id=claims["user_id"])
    from datetime import date, timedelta
    today = date.today()
    return StreakResponse(
        current_streak=streak.current_streak,
        longest_streak=streak.longest_streak,
        last_activity_date=streak.last_activity_date,
        active_today=streak.last_activity_date == today,
    )


@router.get("/me", response_model=StreakResponse)
async def get_my_streak(
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[StreakService, Depends(_get_streak_service)],
) -> StreakResponse:
    return await service.get_streak(user_id=claims["user_id"])


@router.get("/at-risk", response_model=AtRiskResponse)
async def get_at_risk_users(
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[StreakService, Depends(_get_streak_service)],
) -> AtRiskResponse:
    if claims["role"] != "admin":
        raise ForbiddenError("Only admins can view at-risk users")
    user_ids = await service.get_at_risk_user_ids()
    return AtRiskResponse(user_ids=user_ids)
