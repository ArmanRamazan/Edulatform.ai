from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header

from common.errors import AppError, ForbiddenError
from app.domain.models import (
    QuizRequest, QuizResponse, SummaryRequest, SummaryResponse,
    TutorChatRequest, TutorChatResponse, TutorFeedbackRequest, TutorFeedbackResponse,
    CourseOutlineRequest, CourseOutlineResponse,
    LessonContentRequest, LessonContentResponse,
    StudyPlanRequest, StudyPlanResponse,
    ModerationRequest, ModerationResponse,
)
from app.services.ai_service import AIService
from app.services.tutor_service import TutorService
from app.services.credit_service import CreditService
from app.services.study_plan_service import StudyPlanService
from app.services.moderation_service import ModerationService

router = APIRouter(prefix="/ai", tags=["ai"])


def _get_ai_service() -> AIService:
    from app.main import get_ai_service
    return get_ai_service()


def _get_tutor_service() -> TutorService:
    from app.main import get_tutor_service
    return get_tutor_service()


def _get_credit_service() -> CreditService:
    from app.main import get_credit_service
    return get_credit_service()


def _get_study_plan_service() -> StudyPlanService:
    from app.main import get_study_plan_service
    return get_study_plan_service()


def _get_moderation_service() -> ModerationService:
    from app.main import get_moderation_service
    return get_moderation_service()


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


@router.get("/credits/me")
async def credits_me(
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    credit_service: Annotated[CreditService, Depends(_get_credit_service)],
) -> dict:
    return await credit_service.get_status(
        user_id=str(claims["user_id"]),
        tier=claims["subscription_tier"],
    )


@router.post("/quiz/generate", response_model=QuizResponse)
async def generate_quiz(
    body: QuizRequest,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[AIService, Depends(_get_ai_service)],
    credit_service: Annotated[CreditService, Depends(_get_credit_service)],
) -> QuizResponse:
    await credit_service.check_and_consume(
        user_id=str(claims["user_id"]),
        tier=claims["subscription_tier"],
    )
    return await service.generate_quiz(body.lesson_id, body.content)


@router.post("/summary/generate", response_model=SummaryResponse)
async def generate_summary(
    body: SummaryRequest,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[AIService, Depends(_get_ai_service)],
    credit_service: Annotated[CreditService, Depends(_get_credit_service)],
) -> SummaryResponse:
    await credit_service.check_and_consume(
        user_id=str(claims["user_id"]),
        tier=claims["subscription_tier"],
    )
    return await service.generate_summary(body.lesson_id, body.content)


@router.post("/tutor/chat", response_model=TutorChatResponse)
async def tutor_chat(
    body: TutorChatRequest,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[TutorService, Depends(_get_tutor_service)],
    credit_service: Annotated[CreditService, Depends(_get_credit_service)],
) -> TutorChatResponse:
    credits_remaining = await credit_service.check_and_consume(
        user_id=str(claims["user_id"]),
        tier=claims["subscription_tier"],
    )
    return await service.chat(
        user_id=str(claims["user_id"]),
        lesson_id=str(body.lesson_id),
        message=body.message,
        lesson_content=body.lesson_content,
        session_id=body.session_id,
        credits_remaining=credits_remaining,
    )


@router.post("/course/outline", response_model=CourseOutlineResponse)
async def generate_course_outline(
    body: CourseOutlineRequest,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[AIService, Depends(_get_ai_service)],
    credit_service: Annotated[CreditService, Depends(_get_credit_service)],
) -> CourseOutlineResponse:
    if claims["role"] not in ("teacher", "admin"):
        raise ForbiddenError("Only teachers and admins can generate course outlines")
    await credit_service.check_and_consume(
        user_id=str(claims["user_id"]),
        tier=claims["subscription_tier"],
    )
    return await service.generate_outline(
        topic=body.topic,
        level=body.level,
        target_audience=body.target_audience,
        num_modules=body.num_modules,
    )


@router.post("/lesson/generate", response_model=LessonContentResponse)
async def generate_lesson_content(
    body: LessonContentRequest,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[AIService, Depends(_get_ai_service)],
    credit_service: Annotated[CreditService, Depends(_get_credit_service)],
) -> LessonContentResponse:
    if claims["role"] not in ("teacher", "admin"):
        raise ForbiddenError("Only teachers and admins can generate lesson content")
    await credit_service.check_and_consume(
        user_id=str(claims["user_id"]),
        tier=claims["subscription_tier"],
    )
    return await service.generate_lesson_content(
        title=body.title,
        description=body.description,
        course_context=body.course_context,
        format=body.format,
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


@router.post("/study-plan", response_model=StudyPlanResponse)
async def generate_study_plan(
    body: StudyPlanRequest,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[StudyPlanService, Depends(_get_study_plan_service)],
    credit_service: Annotated[CreditService, Depends(_get_credit_service)],
) -> StudyPlanResponse:
    await credit_service.check_and_consume(
        user_id=str(claims["user_id"]),
        tier=claims["subscription_tier"],
    )
    return await service.generate_plan(
        user_id=claims["user_id"],
        course_id=body.course_id,
        available_hours_per_week=body.available_hours_per_week,
        goal=body.goal,
    )


@router.post("/moderate", response_model=ModerationResponse)
async def moderate_content(
    body: ModerationRequest,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[ModerationService, Depends(_get_moderation_service)],
    credit_service: Annotated[CreditService, Depends(_get_credit_service)],
) -> ModerationResponse:
    if claims["role"] not in ("teacher", "admin"):
        raise ForbiddenError("Only teachers and admins can moderate content")
    await credit_service.check_and_consume(
        user_id=str(claims["user_id"]),
        tier=claims["subscription_tier"],
    )
    return await service.moderate(
        content=body.content,
        content_type=body.content_type,
    )
