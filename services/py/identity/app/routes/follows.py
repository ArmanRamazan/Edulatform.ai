from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse, Response

from common.errors import AppError
from app.domain.follow import FollowResponse, FollowStatsResponse, PaginatedFollowsResponse
from app.services.follow_service import FollowService

router = APIRouter(tags=["follows"])


def _get_follow_service() -> FollowService:
    from app.main import get_follow_service
    return get_follow_service()


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


@router.post("/follow/{user_id}", status_code=201)
async def follow_user(
    user_id: UUID,
    current_user_id: Annotated[UUID, Depends(_get_current_user_id)],
    service: Annotated[FollowService, Depends(_get_follow_service)],
) -> JSONResponse:
    follow = await service.follow_user(current_user_id, user_id)
    return JSONResponse(
        status_code=201,
        content=FollowResponse(
            id=follow.id,
            follower_id=follow.follower_id,
            following_id=follow.following_id,
            created_at=follow.created_at,
        ).model_dump(mode="json"),
    )


@router.delete("/follow/{user_id}", status_code=204)
async def unfollow_user(
    user_id: UUID,
    current_user_id: Annotated[UUID, Depends(_get_current_user_id)],
    service: Annotated[FollowService, Depends(_get_follow_service)],
) -> Response:
    await service.unfollow_user(current_user_id, user_id)
    return Response(status_code=204)


@router.get("/followers/me", response_model=PaginatedFollowsResponse)
async def get_my_followers(
    current_user_id: Annotated[UUID, Depends(_get_current_user_id)],
    service: Annotated[FollowService, Depends(_get_follow_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PaginatedFollowsResponse:
    items, total = await service.get_followers(current_user_id, limit, offset)
    return PaginatedFollowsResponse(
        items=[
            FollowResponse(
                id=f.id,
                follower_id=f.follower_id,
                following_id=f.following_id,
                created_at=f.created_at,
            )
            for f in items
        ],
        total=total,
    )


@router.get("/following/me", response_model=PaginatedFollowsResponse)
async def get_my_following(
    current_user_id: Annotated[UUID, Depends(_get_current_user_id)],
    service: Annotated[FollowService, Depends(_get_follow_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PaginatedFollowsResponse:
    items, total = await service.get_following(current_user_id, limit, offset)
    return PaginatedFollowsResponse(
        items=[
            FollowResponse(
                id=f.id,
                follower_id=f.follower_id,
                following_id=f.following_id,
                created_at=f.created_at,
            )
            for f in items
        ],
        total=total,
    )


@router.get("/users/{user_id}/followers/count", response_model=FollowStatsResponse)
async def get_follow_counts(
    user_id: UUID,
    service: Annotated[FollowService, Depends(_get_follow_service)],
) -> FollowStatsResponse:
    stats = await service.get_follow_counts(user_id)
    return FollowStatsResponse(
        followers_count=stats.followers_count,
        following_count=stats.following_count,
    )
