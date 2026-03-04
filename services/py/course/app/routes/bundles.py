from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header, Query, Response

from common.errors import AppError
from app.domain.bundle import BundleCreate, BundleUpdate, BundleResponse, BundleListResponse
from app.domain.course import CourseResponse
from app.services.bundle_service import BundleService

router = APIRouter(prefix="/bundles", tags=["bundles"])


def _get_bundle_service() -> BundleService:
    from app.main import get_bundle_service
    return get_bundle_service()


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


def _to_response(bwc: "BundleWithCourses") -> BundleResponse:
    from app.domain.bundle import BundleWithCourses
    b = bwc.bundle
    return BundleResponse(
        id=b.id,
        teacher_id=b.teacher_id,
        title=b.title,
        description=b.description,
        price=b.price,
        discount_percent=b.discount_percent,
        is_active=b.is_active,
        created_at=b.created_at,
        courses=[
            CourseResponse(
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
            for c in bwc.courses
        ],
    )


def _to_list_item(b: "CourseBundle") -> BundleResponse:
    from app.domain.bundle import CourseBundle
    return BundleResponse(
        id=b.id,
        teacher_id=b.teacher_id,
        title=b.title,
        description=b.description,
        price=b.price,
        discount_percent=b.discount_percent,
        is_active=b.is_active,
        created_at=b.created_at,
        courses=[],
    )


@router.post("", response_model=BundleResponse, status_code=201)
async def create_bundle(
    body: BundleCreate,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[BundleService, Depends(_get_bundle_service)],
) -> BundleResponse:
    bwc = await service.create_bundle(
        teacher_id=claims["user_id"],
        role=claims["role"],
        is_verified=claims["is_verified"],
        title=body.title,
        description=body.description,
        price=body.price,
        discount_percent=body.discount_percent,
        course_ids=body.course_ids,
    )
    return _to_response(bwc)


@router.get("", response_model=BundleListResponse)
async def list_bundles(
    service: Annotated[BundleService, Depends(_get_bundle_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    teacher_id: Annotated[UUID | None, Query()] = None,
) -> BundleListResponse:
    items, total = await service.list_bundles(limit=limit, offset=offset, teacher_id=teacher_id)
    return BundleListResponse(
        items=[_to_list_item(b) for b in items],
        total=total,
    )


@router.get("/{bundle_id}", response_model=BundleResponse)
async def get_bundle(
    bundle_id: UUID,
    service: Annotated[BundleService, Depends(_get_bundle_service)],
) -> BundleResponse:
    bwc = await service.get_bundle(bundle_id)
    return _to_response(bwc)


@router.put("/{bundle_id}", response_model=BundleResponse)
async def update_bundle(
    bundle_id: UUID,
    body: BundleUpdate,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[BundleService, Depends(_get_bundle_service)],
) -> BundleResponse:
    fields = body.model_dump(exclude_none=True)
    bwc = await service.update_bundle(
        teacher_id=claims["user_id"],
        bundle_id=bundle_id,
        **fields,
    )
    return _to_response(bwc)


@router.delete("/{bundle_id}", status_code=204)
async def delete_bundle(
    bundle_id: UUID,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[BundleService, Depends(_get_bundle_service)],
) -> Response:
    await service.delete_bundle(
        teacher_id=claims["user_id"],
        bundle_id=bundle_id,
    )
    return Response(status_code=204)
