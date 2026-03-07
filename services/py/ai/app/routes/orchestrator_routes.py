from __future__ import annotations

from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header

from common.errors import AppError
from app.domain.models import (
    DailyMissionResponse,
    MissionCompleteRequest,
    MissionCompleteResponse,
    MissionDailyRequest,
)
from app.services.credit_service import CreditService
from app.services.orchestrator_service import AgentOrchestrator

router = APIRouter(prefix="/ai/mission", tags=["mission"])


def _get_orchestrator_service() -> AgentOrchestrator:
    from app.main import get_orchestrator_service
    return get_orchestrator_service()


def _get_credit_service() -> CreditService:
    from app.main import get_credit_service
    return get_credit_service()


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


@router.post("/daily", response_model=DailyMissionResponse)
async def get_daily_mission(
    body: MissionDailyRequest,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    orchestrator: Annotated[AgentOrchestrator, Depends(_get_orchestrator_service)],
    credit_service: Annotated[CreditService, Depends(_get_credit_service)],
) -> DailyMissionResponse:
    await credit_service.check_and_consume(
        user_id=str(claims["user_id"]),
        tier=claims["subscription_tier"],
    )
    mastery_data = [
        {"concept_id": str(item.concept_id), "mastery": item.mastery}
        for item in body.mastery
    ]
    mission = await orchestrator.get_daily_mission(
        user_id=claims["user_id"],
        org_id=body.org_id,
        mastery_data=mastery_data,
    )
    return DailyMissionResponse(
        concept_name=mission.concept_name,
        concept_id=mission.concept_id,
        recap_questions=[
            {"question": q.question, "expected_answer": q.expected_answer, "concept_ref": q.concept_ref}
            for q in mission.recap_questions
        ],
        reading_content=mission.reading_content,
        check_questions=[
            {
                "question": q.question,
                "options": q.options,
                "correct_index": q.correct_index,
                "explanation": q.explanation,
            }
            for q in mission.check_questions
        ],
        code_case={
            "code_snippet": mission.code_case.code_snippet,
            "language": mission.code_case.language,
            "question": mission.code_case.question,
            "expected_answer": mission.code_case.expected_answer,
            "source_path": mission.code_case.source_path,
        } if mission.code_case else None,
    )


def _get_coach_service():
    from app.main import get_coach_service
    return get_coach_service()


@router.post("/complete", response_model=MissionCompleteResponse)
async def complete_mission(
    body: MissionCompleteRequest,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    orchestrator: Annotated[AgentOrchestrator, Depends(_get_orchestrator_service)],
    coach: Annotated["CoachService", Depends(_get_coach_service)],
) -> MissionCompleteResponse:
    session_result = await coach.end_session(
        user_id=claims["user_id"],
        session_id=body.session_id,
    )

    result = await orchestrator.complete_session(
        user_id=claims["user_id"],
        org_id=body.org_id,
        session_result=session_result,
        concept_id=body.concept_id,
    )

    return MissionCompleteResponse(
        next_concept_preview=result["next_concept_preview"],
        total_completed=result["total_completed"],
        score=result["score"],
        mastery_delta=result["mastery_delta"],
    )
