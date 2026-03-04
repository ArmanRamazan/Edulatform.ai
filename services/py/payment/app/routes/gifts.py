from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header, Query

from common.errors import AppError
from app.domain.gift import (
    GiftCreate,
    GiftRedeem,
    GiftResponse,
    GiftInfoResponse,
    GiftListResponse,
    GiftPurchase,
)
from app.services.gift_service import GiftService

router = APIRouter(prefix="/gifts", tags=["gifts"])


def _get_gift_service() -> GiftService:
    from app.main import get_gift_service
    return get_gift_service()


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


def _to_response(g: GiftPurchase) -> GiftResponse:
    return GiftResponse(
        id=g.id,
        buyer_id=g.buyer_id,
        recipient_email=g.recipient_email,
        course_id=g.course_id,
        payment_id=g.payment_id,
        gift_code=g.gift_code,
        status=g.status,
        message=g.message,
        created_at=g.created_at,
        redeemed_at=g.redeemed_at,
        redeemed_by=g.redeemed_by,
        expires_at=g.expires_at,
    )


def _to_info_response(g: GiftPurchase) -> GiftInfoResponse:
    return GiftInfoResponse(
        gift_code=g.gift_code,
        course_id=g.course_id,
        status=g.status,
        message=g.message,
        expires_at=g.expires_at,
    )


@router.post("", response_model=GiftResponse, status_code=201)
async def purchase_gift(
    body: GiftCreate,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[GiftService, Depends(_get_gift_service)],
) -> GiftResponse:
    gift = await service.purchase_gift(
        buyer_id=claims["user_id"],
        course_id=body.course_id,
        recipient_email=body.recipient_email,
        message=body.message,
    )
    return _to_response(gift)


@router.get("/me/sent", response_model=GiftListResponse)
async def get_my_sent_gifts(
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[GiftService, Depends(_get_gift_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> GiftListResponse:
    items, total = await service.get_my_sent_gifts(
        claims["user_id"], limit, offset,
    )
    return GiftListResponse(
        items=[_to_response(g) for g in items],
        total=total,
    )


@router.post("/redeem", response_model=GiftResponse)
async def redeem_gift(
    body: GiftRedeem,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[GiftService, Depends(_get_gift_service)],
) -> GiftResponse:
    gift = await service.redeem_gift(
        user_id=claims["user_id"],
        gift_code=body.gift_code,
    )
    return _to_response(gift)


@router.get("/{gift_code}/info", response_model=GiftInfoResponse)
async def get_gift_info(
    gift_code: str,
    service: Annotated[GiftService, Depends(_get_gift_service)],
) -> GiftInfoResponse:
    gift = await service.get_gift_info(gift_code)
    return _to_info_response(gift)
