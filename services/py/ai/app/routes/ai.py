from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header

from common.errors import AppError
from app.domain.models import (
    QuizRequest, QuizResponse, SummaryRequest, SummaryResponse,
    TutorChatRequest, TutorChatResponse, TutorFeedbackRequest, TutorFeedbackResponse,
)
from app.services.ai_service import AIService
from app.services.tutor_service import TutorService

router = APIRouter(prefix="/ai", tags=["ai"])


def _get_ai_service() -> AIService:
    from app.main import get_ai_service
    return get_ai_service()


def _get_tutor_service() -> TutorService:
    from app.main import get_tutor_service
    return get_tutor_service()


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
        }
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise AppError("Invalid token", status_code=401) from exc


@router.post("/quiz/generate", response_model=QuizResponse)
async def generate_quiz(
    body: QuizRequest,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[AIService, Depends(_get_ai_service)],
) -> QuizResponse:
    return await service.generate_quiz(body.lesson_id, body.content)


@router.post("/summary/generate", response_model=SummaryResponse)
async def generate_summary(
    body: SummaryRequest,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[AIService, Depends(_get_ai_service)],
) -> SummaryResponse:
    return await service.generate_summary(body.lesson_id, body.content)


@router.post("/tutor/chat", response_model=TutorChatResponse)
async def tutor_chat(
    body: TutorChatRequest,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[TutorService, Depends(_get_tutor_service)],
) -> TutorChatResponse:
    return await service.chat(
        user_id=str(claims["user_id"]),
        lesson_id=str(body.lesson_id),
        message=body.message,
        lesson_content=body.lesson_content,
        session_id=body.session_id,
    )


@router.post("/tutor/feedback", response_model=TutorFeedbackResponse)
async def tutor_feedback(
    body: TutorFeedbackRequest,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[TutorService, Depends(_get_tutor_service)],
) -> TutorFeedbackResponse:
    return await service.feedback(
        session_id=body.session_id,
        message_index=body.message_index,
        rating=body.rating,
    )
