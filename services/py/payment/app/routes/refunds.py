from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header, Query

from common.errors import AppError
from app.domain.refund import (
    RefundCreate,
    RefundReject,
    RefundResponse,
    RefundListResponse,
)
from app.services.refund_service import RefundService

router = APIRouter(prefix="/refunds", tags=["refunds"])


def _get_refund_service() -> RefundService:
    from app.main import get_refund_service
    return get_refund_service()


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


def _to_response(r: "Refund") -> RefundResponse:
    from app.domain.refund import Refund
    return RefundResponse(
        id=r.id,
        payment_id=r.payment_id,
        user_id=r.user_id,
        reason=r.reason,
        status=r.status,
        amount=r.amount,
        admin_note=r.admin_note,
        requested_at=r.requested_at,
        processed_at=r.processed_at,
    )


@router.post("", response_model=RefundResponse, status_code=201)
async def request_refund(
    body: RefundCreate,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[RefundService, Depends(_get_refund_service)],
) -> RefundResponse:
    refund = await service.request_refund(
        user_id=claims["user_id"],
        payment_id=body.payment_id,
        reason=body.reason,
    )
    return _to_response(refund)


@router.get("/me", response_model=RefundListResponse)
async def get_my_refunds(
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[RefundService, Depends(_get_refund_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> RefundListResponse:
    items, total = await service.get_my_refunds(
        claims["user_id"], limit, offset,
    )
    return RefundListResponse(
        items=[_to_response(r) for r in items],
        total=total,
    )


@router.get("", response_model=RefundListResponse)
async def list_refunds(
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[RefundService, Depends(_get_refund_service)],
    status: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> RefundListResponse:
    items, total = await service.list_refunds(
        role=claims["role"],
        status_filter=status,
        limit=limit,
        offset=offset,
    )
    return RefundListResponse(
        items=[_to_response(r) for r in items],
        total=total,
    )


@router.patch("/{refund_id}/approve", response_model=RefundResponse)
async def approve_refund(
    refund_id: UUID,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[RefundService, Depends(_get_refund_service)],
) -> RefundResponse:
    refund = await service.approve_refund(
        admin_id=claims["user_id"],
        refund_id=refund_id,
        role=claims["role"],
    )
    return _to_response(refund)


@router.patch("/{refund_id}/reject", response_model=RefundResponse)
async def reject_refund(
    refund_id: UUID,
    body: RefundReject,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[RefundService, Depends(_get_refund_service)],
) -> RefundResponse:
    refund = await service.reject_refund(
        admin_id=claims["user_id"],
        refund_id=refund_id,
        role=claims["role"],
        reason=body.reason,
    )
    return _to_response(refund)
