from __future__ import annotations

from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header, Query

from common.errors import AppError
from app.domain.leaderboard import (
    AddScoreRequest,
    LeaderboardResponse,
    MyRankResponse,
    OptInResponse,
)
from app.services.leaderboard_service import LeaderboardService

router = APIRouter(prefix="/leaderboards", tags=["leaderboards"])


def _get_leaderboard_service() -> LeaderboardService:
    from app.main import get_leaderboard_service
    return get_leaderboard_service()


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


@router.post("/courses/{course_id}/opt-in", response_model=OptInResponse)
async def opt_in(
    course_id: UUID,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[LeaderboardService, Depends(_get_leaderboard_service)],
) -> OptInResponse:
    return await service.opt_in(claims["user_id"], course_id)


@router.delete("/courses/{course_id}/opt-in", response_model=OptInResponse)
async def opt_out(
    course_id: UUID,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[LeaderboardService, Depends(_get_leaderboard_service)],
) -> OptInResponse:
    return await service.opt_out(claims["user_id"], course_id)


@router.get("/courses/{course_id}", response_model=LeaderboardResponse)
async def get_leaderboard(
    course_id: UUID,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[LeaderboardService, Depends(_get_leaderboard_service)],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> LeaderboardResponse:
    return await service.get_leaderboard(course_id, limit=limit, offset=offset)


@router.get("/courses/{course_id}/me", response_model=MyRankResponse)
async def get_my_rank(
    course_id: UUID,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[LeaderboardService, Depends(_get_leaderboard_service)],
) -> MyRankResponse:
    return await service.get_my_rank(claims["user_id"], course_id)


@router.post("/courses/{course_id}/score", response_model=OptInResponse)
async def add_score(
    course_id: UUID,
    body: AddScoreRequest,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[LeaderboardService, Depends(_get_leaderboard_service)],
) -> OptInResponse:
    return await service.add_score(claims["user_id"], course_id, body.points)
