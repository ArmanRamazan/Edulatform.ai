from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query

from common.errors import AppError
from app.domain.recommendation import CourseRecommendation, RecommendationListResponse
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def _get_recommendation_service() -> RecommendationService:
    from app.main import get_recommendation_service
    return get_recommendation_service()


def _get_current_user_id(authorization: Annotated[str, Header()]) -> UUID:
    import jwt as pyjwt
    from app.main import app_settings

    if not authorization.startswith("Bearer "):
        raise AppError("Invalid authorization header", status_code=401)
    token = authorization[7:]
    try:
        payload = pyjwt.decode(
            token, app_settings.jwt_secret, algorithms=[app_settings.jwt_algorithm]
        )
        return UUID(payload["sub"])
    except (pyjwt.PyJWTError, ValueError, KeyError) as exc:
        raise AppError("Invalid token", status_code=401) from exc


@router.get(
    "/courses/{course_id}",
    response_model=RecommendationListResponse,
    description="Get courses similar to this one based on co-enrollment patterns",
)
async def get_similar_courses(
    course_id: UUID,
    service: Annotated[RecommendationService, Depends(_get_recommendation_service)],
    limit: Annotated[int, Query(ge=1, le=50)] = 5,
) -> RecommendationListResponse:
    results = await service.get_similar_courses(course_id, limit=limit)
    return RecommendationListResponse(
        items=[CourseRecommendation(**r) for r in results]
    )


@router.get(
    "/me",
    response_model=RecommendationListResponse,
    description="Get personalized course recommendations for the current user",
)
async def get_personalized_recommendations(
    user_id: Annotated[UUID, Depends(_get_current_user_id)],
    service: Annotated[RecommendationService, Depends(_get_recommendation_service)],
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> RecommendationListResponse:
    results = await service.get_personalized_recommendations(user_id, limit=limit)
    return RecommendationListResponse(
        items=[CourseRecommendation(**r) for r in results]
    )
