from __future__ import annotations

from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header, Query

from common.errors import AppError
from app.domain.xp import XpSummaryResponse
from app.services.xp_service import XpService

router = APIRouter(prefix="/xp", tags=["xp"])


def _get_xp_service() -> XpService:
    from app.main import get_xp_service
    return get_xp_service()


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


@router.get("/me", response_model=XpSummaryResponse)
async def get_my_xp(
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[XpService, Depends(_get_xp_service)],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> XpSummaryResponse:
    return await service.get_summary(
        user_id=claims["user_id"], limit=limit, offset=offset,
    )
