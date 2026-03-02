from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header

from common.errors import AppError
from app.domain.course import TeacherAnalyticsSummary
from app.services.course_service import CourseService

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _get_course_service() -> CourseService:
    from app.main import get_course_service
    return get_course_service()


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


@router.get("/teacher", response_model=TeacherAnalyticsSummary)
async def get_teacher_analytics(
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[CourseService, Depends(_get_course_service)],
) -> TeacherAnalyticsSummary:
    return await service.get_teacher_analytics(claims["user_id"], claims["role"])
