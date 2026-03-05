from __future__ import annotations

from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel

from common.errors import AppError
from app.services.daily_service import DailyService

router = APIRouter(prefix="/daily", tags=["daily"])


def _get_daily_service() -> DailyService:
    from app.main import get_daily_service
    return get_daily_service()


def _get_current_user_claims(authorization: Annotated[str, Header()]) -> dict:
    from app.main import app_settings

    if not authorization.startswith("Bearer "):
        raise AppError("Invalid authorization header", status_code=401)
    token = authorization[7:]
    try:
        payload = jwt.decode(
            token, app_settings.jwt_secret, algorithms=[app_settings.jwt_algorithm],
        )
        return {
            "user_id": UUID(payload["sub"]),
            "role": payload.get("role", "student"),
            "is_verified": payload.get("is_verified", False),
            "token": token,
        }
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise AppError("Invalid token", status_code=401) from exc


# --- Response models ---


class MissionSummaryResponse(BaseModel):
    id: UUID
    concept_id: UUID | None
    mission_type: str
    status: str
    blueprint: dict
    score: float | None
    mastery_delta: float | None


class TrustLevelSummaryResponse(BaseModel):
    level: int
    total_missions_completed: int
    total_concepts_mastered: int
    unlocked_areas: list[str]


class DailySummaryResponse(BaseModel):
    mission: MissionSummaryResponse | None
    trust_level: TrustLevelSummaryResponse
    due_flashcards: int
    streak_days: int
    greeting: str


@router.get("/me", response_model=DailySummaryResponse)
async def get_daily_summary(
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[DailyService, Depends(_get_daily_service)],
    org_id: UUID = Query(...),
) -> DailySummaryResponse:
    summary = await service.get_daily_summary(
        user_id=claims["user_id"],
        org_id=org_id,
        token=claims["token"],
    )

    mission_resp = None
    if summary.mission is not None:
        m = summary.mission
        mission_resp = MissionSummaryResponse(
            id=m.id,
            concept_id=m.concept_id,
            mission_type=m.mission_type,
            status=m.status,
            blueprint=m.blueprint,
            score=m.score,
            mastery_delta=m.mastery_delta,
        )

    tl = summary.trust_level
    trust_resp = TrustLevelSummaryResponse(
        level=tl.level,
        total_missions_completed=tl.total_missions_completed,
        total_concepts_mastered=tl.total_concepts_mastered,
        unlocked_areas=tl.unlocked_areas,
    )

    return DailySummaryResponse(
        mission=mission_resp,
        trust_level=trust_resp,
        due_flashcards=summary.due_flashcards,
        streak_days=summary.streak_days,
        greeting=summary.greeting,
    )
