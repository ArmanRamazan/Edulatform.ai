from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header, Query

from common.errors import AppError
from app.domain.course import CourseSortField, CourseCreate, CourseUpdate, CourseResponse, CourseListResponse, CurriculumResponse
from app.services.course_service import CourseService

router = APIRouter(prefix="/courses", tags=["courses"])


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


def _to_response(c: "Course") -> CourseResponse:
    from app.domain.course import Course
    return CourseResponse(
        id=c.id,
        teacher_id=c.teacher_id,
        title=c.title,
        description=c.description,
        is_free=c.is_free,
        price=c.price,
        duration_minutes=c.duration_minutes,
        level=c.level,
        created_at=c.created_at,
        avg_rating=c.avg_rating,
        review_count=c.review_count,
        category_id=c.category_id,
    )


@router.get("", response_model=CourseListResponse)
async def list_courses(
    service: Annotated[CourseService, Depends(_get_course_service)],
    q: Annotated[str | None, Query()] = None,
    category_id: Annotated[UUID | None, Query()] = None,
    level: Annotated[str | None, Query()] = None,
    is_free: Annotated[bool | None, Query()] = None,
    sort_by: Annotated[CourseSortField, Query()] = CourseSortField.CREATED_AT,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    cursor: Annotated[str | None, Query()] = None,
) -> CourseListResponse:
    has_filters = category_id is not None or level is not None or is_free is not None or sort_by != "created_at"
    if has_filters or cursor is None:
        if has_filters or q:
            items, total = await service.list_filtered(
                limit=limit, offset=offset, category_id=category_id,
                level=level, is_free=is_free, q=q, sort_by=sort_by,
            )
            return CourseListResponse(items=[_to_response(c) for c in items], total=total)
    if cursor is not None:
        if q:
            items, total, next_cursor = await service.search_cursor(q, limit, cursor)
        else:
            items, total, next_cursor = await service.list_cursor(limit, cursor)
        return CourseListResponse(
            items=[_to_response(c) for c in items],
            total=total,
            next_cursor=next_cursor,
        )
    items, total = await service.list(limit, offset)
    return CourseListResponse(
        items=[_to_response(c) for c in items],
        total=total,
    )


@router.get("/my", response_model=CourseListResponse)
async def list_my_courses(
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[CourseService, Depends(_get_course_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    cursor: Annotated[str | None, Query()] = None,
) -> CourseListResponse:
    if cursor is not None:
        items, total, next_cursor = await service.list_my_cursor(
            claims["user_id"], limit, cursor
        )
        return CourseListResponse(
            items=[_to_response(c) for c in items],
            total=total,
            next_cursor=next_cursor,
        )
    items, total = await service.list_my(claims["user_id"], limit, offset)
    return CourseListResponse(
        items=[_to_response(c) for c in items],
        total=total,
    )


@router.get("/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: UUID,
    service: Annotated[CourseService, Depends(_get_course_service)],
) -> CourseResponse:
    c = await service.get(course_id)
    return _to_response(c)


@router.get("/{course_id}/curriculum", response_model=CurriculumResponse)
async def get_curriculum(
    course_id: UUID,
    service: Annotated[CourseService, Depends(_get_course_service)],
) -> CurriculumResponse:
    return await service.get_curriculum(course_id)


@router.post("", response_model=CourseResponse, status_code=201)
async def create_course(
    body: CourseCreate,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[CourseService, Depends(_get_course_service)],
) -> CourseResponse:
    c = await service.create(
        teacher_id=claims["user_id"],
        role=claims["role"],
        is_verified=claims["is_verified"],
        title=body.title,
        description=body.description,
        is_free=body.is_free,
        price=body.price,
        duration_minutes=body.duration_minutes,
        level=body.level,
        category_id=body.category_id,
    )
    return _to_response(c)


@router.put("/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: UUID,
    body: CourseUpdate,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[CourseService, Depends(_get_course_service)],
) -> CourseResponse:
    fields = body.model_dump(exclude_none=True)
    c = await service.update(
        course_id=course_id,
        teacher_id=claims["user_id"],
        role=claims["role"],
        is_verified=claims["is_verified"],
        **fields,
    )
    return _to_response(c)
