from __future__ import annotations

from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header, Query

from common.errors import AppError
from app.domain.activity import ActivityListResponse, ActivityResponse
from app.services.activity_service import ActivityService

router = APIRouter(prefix="/activity", tags=["activity"])


def _get_activity_service() -> ActivityService:
    from app.main import get_activity_service
    return get_activity_service()


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


@router.get("/me", response_model=ActivityListResponse)
async def get_my_activity(
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[ActivityService, Depends(_get_activity_service)],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ActivityListResponse:
    activities = await service.get_my_activity(
        user_id=claims["user_id"], limit=limit, offset=offset,
    )
    return ActivityListResponse(
        activities=[
            ActivityResponse(
                id=a.id, user_id=a.user_id, activity_type=a.activity_type,
                payload=a.payload, created_at=a.created_at,
            )
            for a in activities
        ],
        total=len(activities),
    )


@router.get("/feed", response_model=ActivityListResponse)
async def get_social_feed(
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[ActivityService, Depends(_get_activity_service)],
    user_ids: str = Query(description="Comma-separated user UUIDs"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ActivityListResponse:
    parsed_ids: list[UUID] = []
    if user_ids:
        for uid_str in user_ids.split(","):
            uid_str = uid_str.strip()
            if uid_str:
                try:
                    parsed_ids.append(UUID(uid_str))
                except ValueError:
                    raise AppError(f"Invalid UUID: {uid_str}", status_code=400)

    activities = await service.get_social_feed(
        user_ids=parsed_ids, limit=limit, offset=offset,
    )
    return ActivityListResponse(
        activities=[
            ActivityResponse(
                id=a.id, user_id=a.user_id, activity_type=a.activity_type,
                payload=a.payload, created_at=a.created_at,
            )
            for a in activities
        ],
        total=len(activities),
    )
