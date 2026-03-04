from __future__ import annotations

from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header, Query, Response

from common.errors import AppError
from app.domain.coupon import (
    Coupon,
    CouponCreate,
    CouponValidate,
    CouponResponse,
    CouponListResponse,
    DiscountResultResponse,
)
from app.services.coupon_service import CouponService

router = APIRouter(prefix="/coupons", tags=["coupons"])


def _get_coupon_service() -> CouponService:
    from app.main import get_coupon_service
    return get_coupon_service()


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


def _to_response(c: Coupon) -> CouponResponse:
    return CouponResponse(
        id=c.id,
        code=c.code,
        discount_type=c.discount_type,
        discount_value=c.discount_value,
        max_uses=c.max_uses,
        current_uses=c.current_uses,
        valid_from=c.valid_from,
        valid_until=c.valid_until,
        course_id=c.course_id,
        created_by=c.created_by,
        is_active=c.is_active,
        created_at=c.created_at,
    )


@router.post("", response_model=CouponResponse, status_code=201)
async def create_coupon(
    body: CouponCreate,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[CouponService, Depends(_get_coupon_service)],
) -> CouponResponse:
    coupon = await service.create_coupon(
        admin_id=claims["user_id"],
        role=claims["role"],
        code=body.code,
        discount_type=body.discount_type,
        discount_value=body.discount_value,
        max_uses=body.max_uses,
        valid_from=body.valid_from,
        valid_until=body.valid_until,
        course_id=body.course_id,
    )
    return _to_response(coupon)


@router.get("", response_model=CouponListResponse)
async def list_coupons(
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[CouponService, Depends(_get_coupon_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> CouponListResponse:
    items, total = await service.list_coupons(
        role=claims["role"], limit=limit, offset=offset,
    )
    return CouponListResponse(
        items=[_to_response(c) for c in items],
        total=total,
    )


@router.post("/validate", response_model=DiscountResultResponse)
async def validate_coupon(
    body: CouponValidate,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[CouponService, Depends(_get_coupon_service)],
) -> DiscountResultResponse:
    result = await service.validate_coupon(
        code=body.code,
        course_id=body.course_id,
        user_id=claims["user_id"],
        original_price=body.amount,
    )
    return DiscountResultResponse(
        original_price=result.original_price,
        discount_amount=result.discount_amount,
        final_price=result.final_price,
        coupon_code=result.coupon_code,
    )


@router.patch("/{coupon_id}/deactivate", status_code=204)
async def deactivate_coupon(
    coupon_id: UUID,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[CouponService, Depends(_get_coupon_service)],
) -> Response:
    await service.deactivate_coupon(
        admin_id=claims["user_id"],
        role=claims["role"],
        coupon_id=coupon_id,
    )
    return Response(status_code=204)
