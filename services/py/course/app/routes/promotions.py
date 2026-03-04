from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header, Response

from common.errors import AppError
from app.domain.promotion import (
    ActivePromotionResponse,
    PromotionCreate,
    PromotionListResponse,
    PromotionResponse,
)
from app.services.promotion_service import PromotionService

router = APIRouter(tags=["promotions"])


def _get_promotion_service() -> PromotionService:
    from app.main import get_promotion_service
    return get_promotion_service()


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


def _to_response(p: "CoursePromotion") -> PromotionResponse:
    return PromotionResponse(
        id=p.id,
        course_id=p.course_id,
        original_price=p.original_price,
        promo_price=p.promo_price,
        starts_at=p.starts_at,
        ends_at=p.ends_at,
        is_active=p.is_active,
        created_by=p.created_by,
        created_at=p.created_at,
    )


@router.post("/courses/{course_id}/promotions", response_model=PromotionResponse, status_code=201)
async def create_promotion(
    course_id: UUID,
    body: PromotionCreate,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[PromotionService, Depends(_get_promotion_service)],
) -> PromotionResponse:
    promo = await service.create_promotion(
        teacher_id=claims["user_id"],
        course_id=course_id,
        promo_price=body.promo_price,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
    )
    return _to_response(promo)


@router.get("/courses/{course_id}/promotions", response_model=PromotionListResponse)
async def get_course_promotions(
    course_id: UUID,
    service: Annotated[PromotionService, Depends(_get_promotion_service)],
) -> PromotionListResponse:
    active = await service.get_active_promotion(course_id)
    if active:
        return PromotionListResponse(items=[
            PromotionResponse(
                id=UUID("00000000-0000-0000-0000-000000000000"),
                course_id=course_id,
                original_price=active.promo_price,
                promo_price=active.promo_price,
                starts_at=active.ends_at,
                ends_at=active.ends_at,
                is_active=True,
                created_by=UUID("00000000-0000-0000-0000-000000000000"),
                created_at=active.ends_at,
            ),
        ])
    return PromotionListResponse(items=[])


@router.delete("/promotions/{promotion_id}", status_code=204)
async def delete_promotion(
    promotion_id: UUID,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[PromotionService, Depends(_get_promotion_service)],
) -> Response:
    await service.delete_promotion(
        teacher_id=claims["user_id"],
        promotion_id=promotion_id,
    )
    return Response(status_code=204)
