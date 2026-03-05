from __future__ import annotations

from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header, Query

from common.errors import AppError, ForbiddenError
from app.domain.trust_level import (
    LEVEL_NAMES,
    LEVEL_THRESHOLDS,
    NextLevelProgress,
    TrustLevelListResponse,
    TrustLevelResponse,
)
from app.services.trust_level_service import TrustLevelService

router = APIRouter(prefix="/trust-level", tags=["trust-level"])


def _get_trust_level_service() -> TrustLevelService:
    from app.main import get_trust_level_service
    return get_trust_level_service()


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


def _build_response(tl) -> TrustLevelResponse:  # type: ignore[no-untyped-def]
    next_level = None
    next_lvl = tl.level + 1
    if next_lvl in LEVEL_THRESHOLDS:
        threshold = LEVEL_THRESHOLDS[next_lvl]
        next_level = NextLevelProgress(
            level=next_lvl,
            level_name=LEVEL_NAMES[next_lvl],
            missions_required=threshold["missions"],
            concepts_required=threshold["concepts_mastered"],
            missions_remaining=max(0, threshold["missions"] - tl.total_missions_completed),
            concepts_remaining=max(0, threshold["concepts_mastered"] - tl.total_concepts_mastered),
        )
    return TrustLevelResponse(
        id=tl.id,
        user_id=tl.user_id,
        organization_id=tl.organization_id,
        level=tl.level,
        level_name=LEVEL_NAMES.get(tl.level, "Unknown"),
        total_missions_completed=tl.total_missions_completed,
        total_concepts_mastered=tl.total_concepts_mastered,
        unlocked_areas=tl.unlocked_areas,
        level_up_at=tl.level_up_at,
        next_level=next_level,
    )


@router.get("/me", response_model=TrustLevelResponse)
async def get_my_trust_level(
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[TrustLevelService, Depends(_get_trust_level_service)],
    org_id: UUID = Query(...),
) -> TrustLevelResponse:
    tl = await service.get_my_level(user_id=claims["user_id"], org_id=org_id)
    return _build_response(tl)


@router.get("/org/{org_id}", response_model=TrustLevelListResponse)
async def get_org_trust_levels(
    org_id: UUID,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[TrustLevelService, Depends(_get_trust_level_service)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> TrustLevelListResponse:
    if claims["role"] != "admin":
        raise ForbiddenError("Only admins can view organization trust levels")
    levels = await service.get_org_levels(org_id, limit, offset)
    return TrustLevelListResponse(
        levels=[_build_response(tl) for tl in levels],
    )
