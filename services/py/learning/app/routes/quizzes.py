from __future__ import annotations

from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header, Query

from common.errors import AppError
from app.domain.quiz import (
    QuizCreate,
    QuizResponse,
    QuestionResponse,
    AttemptSubmit,
    AttemptResponse,
    QuestionResult,
    AttemptListResponse,
    AttemptSummary,
)
from app.services.quiz_service import QuizService

router = APIRouter(prefix="/quizzes", tags=["quizzes"])


def _get_quiz_service() -> QuizService:
    from app.main import get_quiz_service
    return get_quiz_service()


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


@router.post("", response_model=QuizResponse, status_code=201)
async def create_quiz(
    body: QuizCreate,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[QuizService, Depends(_get_quiz_service)],
) -> QuizResponse:
    quiz, questions = await service.create_quiz(
        teacher_id=claims["user_id"],
        role=claims["role"],
        is_verified=claims["is_verified"],
        lesson_id=body.lesson_id,
        course_id=body.course_id,
        questions=[q.model_dump() for q in body.questions],
    )
    return QuizResponse(
        id=quiz.id,
        lesson_id=quiz.lesson_id,
        course_id=quiz.course_id,
        questions=[
            QuestionResponse(id=q.id, text=q.text, options=q.options, order=q.order)
            for q in questions
        ],
        created_at=quiz.created_at,
    )


@router.get("/lesson/{lesson_id}", response_model=QuizResponse)
async def get_quiz_by_lesson(
    lesson_id: UUID,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[QuizService, Depends(_get_quiz_service)],
) -> QuizResponse:
    quiz, questions = await service.get_quiz_by_lesson(lesson_id)
    return QuizResponse(
        id=quiz.id,
        lesson_id=quiz.lesson_id,
        course_id=quiz.course_id,
        questions=[
            QuestionResponse(id=q.id, text=q.text, options=q.options, order=q.order)
            for q in questions
        ],
        created_at=quiz.created_at,
    )


@router.post("/{quiz_id}/submit", response_model=AttemptResponse)
async def submit_quiz(
    quiz_id: UUID,
    body: AttemptSubmit,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[QuizService, Depends(_get_quiz_service)],
) -> AttemptResponse:
    attempt, results = await service.submit_quiz(
        quiz_id=quiz_id,
        student_id=claims["user_id"],
        role=claims["role"],
        answers=body.answers,
    )
    correct_count = sum(1 for r in results if r.is_correct)
    return AttemptResponse(
        id=attempt.id,
        quiz_id=attempt.quiz_id,
        score=attempt.score,
        total_questions=len(results),
        correct_count=correct_count,
        results=results,
        completed_at=attempt.completed_at,
    )


@router.get("/{quiz_id}/attempts/me", response_model=AttemptListResponse)
async def list_my_attempts(
    quiz_id: UUID,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[QuizService, Depends(_get_quiz_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AttemptListResponse:
    items, total = await service.list_my_attempts(
        quiz_id=quiz_id,
        student_id=claims["user_id"],
        limit=limit,
        offset=offset,
    )
    return AttemptListResponse(
        items=[
            AttemptSummary(id=a.id, score=a.score, completed_at=a.completed_at)
            for a in items
        ],
        total=total,
    )
