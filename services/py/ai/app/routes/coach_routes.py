from __future__ import annotations

from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header

from common.errors import AppError
from app.domain.models import (
    CoachStartRequest,
    CoachStartResponse,
    CoachChatRequest,
    CoachChatResponse,
    CoachEndRequest,
    CoachEndResponse,
)
from app.services.coach_service import CoachService
from app.services.credit_service import CreditService
from app.services.designer_service import DesignerService

router = APIRouter(prefix="/ai/coach", tags=["coach"])


def _get_coach_service() -> CoachService:
    from app.main import get_coach_service
    return get_coach_service()


def _get_credit_service() -> CreditService:
    from app.main import get_credit_service
    return get_credit_service()


def _get_designer_service() -> DesignerService:
    from app.main import get_designer_service
    return get_designer_service()


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
            "subscription_tier": payload.get("subscription_tier", "free"),
        }
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise AppError("Invalid token", status_code=401) from exc


@router.post("/start", response_model=CoachStartResponse)
async def coach_start(
    body: CoachStartRequest,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    coach: Annotated[CoachService, Depends(_get_coach_service)],
    credit_service: Annotated[CreditService, Depends(_get_credit_service)],
    designer: Annotated[DesignerService, Depends(_get_designer_service)],
) -> CoachStartResponse:
    await credit_service.check_and_consume(
        user_id=str(claims["user_id"]),
        tier=claims["subscription_tier"],
    )
    mission = await designer.design_mission(
        concept_name="",
        concept_id=body.mission_id,
        org_id=claims["user_id"],
    )
    result = await coach.start_session(
        user_id=claims["user_id"],
        mission=mission,
        personality=body.personality,
    )
    return CoachStartResponse(
        session_id=result.session_id,
        content=result.content,
        phase=result.phase,
        phase_progress=result.phase_progress,
    )


@router.post("/chat", response_model=CoachChatResponse)
async def coach_chat(
    body: CoachChatRequest,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    coach: Annotated[CoachService, Depends(_get_coach_service)],
    credit_service: Annotated[CreditService, Depends(_get_credit_service)],
) -> CoachChatResponse:
    await credit_service.check_and_consume(
        user_id=str(claims["user_id"]),
        tier=claims["subscription_tier"],
    )
    result = await coach.chat(
        user_id=claims["user_id"],
        session_id=body.session_id,
        message=body.message,
    )
    return CoachChatResponse(
        session_id=result.session_id,
        content=result.content,
        phase=result.phase,
        phase_progress=result.phase_progress,
    )


@router.post("/end", response_model=CoachEndResponse)
async def coach_end(
    body: CoachEndRequest,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    coach: Annotated[CoachService, Depends(_get_coach_service)],
) -> CoachEndResponse:
    result = await coach.end_session(
        user_id=claims["user_id"],
        session_id=body.session_id,
    )
    return CoachEndResponse(
        session_id=result.session_id,
        score=result.score,
        mastery_delta=result.mastery_delta,
        duration_seconds=result.duration_seconds,
        strengths=result.strengths,
        gaps=result.gaps,
    )
