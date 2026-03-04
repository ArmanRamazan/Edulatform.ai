from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.domain.referral import (
    ApplyReferralRequest,
    CompleteReferralRequest,
    ReferralResponse,
    ReferralStatsResponse,
)
from app.routes.auth import _get_current_user_id
from app.services.referral_service import ReferralService

router = APIRouter(prefix="/referral", tags=["referral"])


def _get_referral_service() -> ReferralService:
    from app.main import get_referral_service
    return get_referral_service()


def _get_auth_service():  # type: ignore[no-untyped-def]
    from app.main import get_auth_service
    return get_auth_service()


@router.get("/me", response_model=ReferralStatsResponse)
async def get_referral_stats(
    user_id: Annotated[UUID, Depends(_get_current_user_id)],
    service: Annotated[ReferralService, Depends(_get_referral_service)],
) -> ReferralStatsResponse:
    stats = await service.get_my_referral_info(user_id)
    return ReferralStatsResponse(
        referral_code=stats.referral_code,
        invited_count=stats.invited_count,
        completed_count=stats.completed_count,
        rewards_earned=stats.rewards_earned,
    )


@router.post("/apply", status_code=201, response_model=ReferralResponse)
async def apply_referral(
    body: ApplyReferralRequest,
    user_id: Annotated[UUID, Depends(_get_current_user_id)],
    service: Annotated[ReferralService, Depends(_get_referral_service)],
) -> JSONResponse:
    referral = await service.apply_referral_code(user_id, body.referral_code)
    return JSONResponse(
        status_code=201,
        content=ReferralResponse(
            id=referral.id,
            referrer_id=referral.referrer_id,
            referee_id=referral.referee_id,
            referral_code=referral.referral_code,
            status=referral.status,
            reward_type=referral.reward_type,
            created_at=referral.created_at,
            completed_at=referral.completed_at,
        ).model_dump(mode="json"),
    )


@router.post("/complete", response_model=ReferralResponse)
async def complete_referral(
    body: CompleteReferralRequest,
    service: Annotated[ReferralService, Depends(_get_referral_service)],
) -> ReferralResponse:
    referral = await service.complete_referral(body.referee_id)
    return ReferralResponse(
        id=referral.id,
        referrer_id=referral.referrer_id,
        referee_id=referral.referee_id,
        referral_code=referral.referral_code,
        status=referral.status,
        reward_type=referral.reward_type,
        created_at=referral.created_at,
        completed_at=referral.completed_at,
    )
