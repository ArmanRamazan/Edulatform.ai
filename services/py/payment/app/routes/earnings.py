from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header, Query

from common.errors import AppError
from app.domain.payment import (
    EarningListResponse,
    EarningResponse,
    EarningsSummary,
    PayoutCreate,
    PayoutListResponse,
    PayoutResponse,
)
from app.services.earnings_service import EarningsService

router = APIRouter(prefix="/earnings", tags=["earnings"])


def _get_earnings_service() -> EarningsService:
    from app.main import get_earnings_service
    return get_earnings_service()


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


def _to_earning_response(e: "TeacherEarning") -> EarningResponse:
    from app.domain.payment import TeacherEarning
    return EarningResponse(
        id=e.id,
        teacher_id=e.teacher_id,
        course_id=e.course_id,
        payment_id=e.payment_id,
        gross_amount=e.gross_amount,
        commission_rate=e.commission_rate,
        net_amount=e.net_amount,
        status=e.status,
        created_at=e.created_at,
    )


def _to_payout_response(p: "Payout") -> PayoutResponse:
    from app.domain.payment import Payout
    return PayoutResponse(
        id=p.id,
        teacher_id=p.teacher_id,
        amount=p.amount,
        stripe_transfer_id=p.stripe_transfer_id,
        status=p.status,
        requested_at=p.requested_at,
        completed_at=p.completed_at,
    )


@router.get("/me/summary", response_model=EarningsSummary)
async def get_earnings_summary(
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[EarningsService, Depends(_get_earnings_service)],
) -> EarningsSummary:
    return await service.get_summary(claims["user_id"], role=claims["role"])


@router.get("/me", response_model=EarningListResponse)
async def list_my_earnings(
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[EarningsService, Depends(_get_earnings_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> EarningListResponse:
    items, total = await service.list_earnings(
        claims["user_id"], role=claims["role"], limit=limit, offset=offset
    )
    return EarningListResponse(
        items=[_to_earning_response(e) for e in items],
        total=total,
    )


@router.post("/payouts", response_model=PayoutResponse, status_code=201)
async def request_payout(
    body: PayoutCreate,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[EarningsService, Depends(_get_earnings_service)],
) -> PayoutResponse:
    payout = await service.request_payout(
        claims["user_id"], role=claims["role"], amount=body.amount
    )
    return _to_payout_response(payout)


@router.get("/payouts", response_model=PayoutListResponse)
async def list_payouts(
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[EarningsService, Depends(_get_earnings_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PayoutListResponse:
    items, total = await service.list_payouts(
        claims["user_id"], role=claims["role"], limit=limit, offset=offset
    )
    return PayoutListResponse(
        items=[_to_payout_response(p) for p in items],
        total=total,
    )
