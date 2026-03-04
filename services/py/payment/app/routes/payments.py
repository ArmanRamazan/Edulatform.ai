from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header, Query

from common.errors import AppError
from app.domain.payment import (
    PaymentCreate,
    PaymentResponse,
    PaymentListResponse,
)
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["payments"])


def _get_payment_service() -> PaymentService:
    from app.main import get_payment_service
    return get_payment_service()


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


def _to_response(p: "Payment") -> PaymentResponse:
    from app.domain.payment import Payment
    return PaymentResponse(
        id=p.id,
        student_id=p.student_id,
        course_id=p.course_id,
        amount=p.amount,
        status=p.status,
        created_at=p.created_at,
    )


def _get_coupon_service():
    from app.main import get_coupon_service
    return get_coupon_service()


@router.post("", response_model=PaymentResponse, status_code=201)
async def create_payment(
    body: PaymentCreate,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[PaymentService, Depends(_get_payment_service)],
) -> PaymentResponse:
    amount = body.amount
    coupon_code = body.coupon_code

    if coupon_code:
        from app.services.coupon_service import CouponService
        coupon_svc: CouponService = _get_coupon_service()
        discount = await coupon_svc.validate_coupon(
            code=coupon_code,
            course_id=body.course_id,
            user_id=claims["user_id"],
            original_price=amount,
        )
        amount = discount.final_price

    payment = await service.create(
        student_id=claims["user_id"],
        role=claims["role"],
        course_id=body.course_id,
        amount=amount,
    )

    if coupon_code:
        await coupon_svc.apply_coupon(
            code=coupon_code,
            user_id=claims["user_id"],
            payment_id=payment.id,
        )

    return _to_response(payment)


@router.get("/me", response_model=PaymentListResponse)
async def list_my_payments(
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[PaymentService, Depends(_get_payment_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PaymentListResponse:
    items, total = await service.list_my(claims["user_id"], limit, offset)
    return PaymentListResponse(
        items=[_to_response(p) for p in items],
        total=total,
    )


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: UUID,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[PaymentService, Depends(_get_payment_service)],
) -> PaymentResponse:
    p = await service.get(payment_id)
    return _to_response(p)
