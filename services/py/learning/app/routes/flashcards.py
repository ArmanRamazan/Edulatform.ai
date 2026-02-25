from __future__ import annotations

from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header, Query

from common.errors import AppError
from app.domain.flashcard import (
    FlashcardCreate,
    FlashcardResponse,
    ReviewSubmit,
    ReviewResponse,
    DueCardsResponse,
)
from app.services.flashcard_service import FlashcardService

router = APIRouter(prefix="/flashcards", tags=["flashcards"])


def _get_flashcard_service() -> FlashcardService:
    from app.main import get_flashcard_service
    return get_flashcard_service()


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


@router.post("", response_model=FlashcardResponse, status_code=201)
async def create_flashcard(
    body: FlashcardCreate,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[FlashcardService, Depends(_get_flashcard_service)],
) -> FlashcardResponse:
    card = await service.create_card(
        student_id=claims["user_id"],
        role=claims["role"],
        course_id=body.course_id,
        concept=body.concept,
        answer=body.answer,
        source_type=body.source_type,
        source_id=body.source_id,
    )
    return FlashcardResponse(
        id=card.id,
        course_id=card.course_id,
        concept=card.concept,
        answer=card.answer,
        source_type=card.source_type,
        stability=card.stability,
        difficulty=card.difficulty,
        due=card.due,
        state=card.state,
        reps=card.reps,
        lapses=card.lapses,
        created_at=card.created_at,
    )


@router.get("/due", response_model=DueCardsResponse)
async def get_due_cards(
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[FlashcardService, Depends(_get_flashcard_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DueCardsResponse:
    cards, total = await service.get_due_cards(
        student_id=claims["user_id"],
        limit=limit,
        offset=offset,
    )
    return DueCardsResponse(
        items=[
            FlashcardResponse(
                id=c.id, course_id=c.course_id, concept=c.concept,
                answer=c.answer, source_type=c.source_type,
                stability=c.stability, difficulty=c.difficulty,
                due=c.due, state=c.state, reps=c.reps,
                lapses=c.lapses, created_at=c.created_at,
            )
            for c in cards
        ],
        total=total,
    )


@router.post("/{card_id}/review", response_model=ReviewResponse)
async def review_flashcard(
    card_id: UUID,
    body: ReviewSubmit,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[FlashcardService, Depends(_get_flashcard_service)],
) -> ReviewResponse:
    _updated, scheduling = await service.review_card(
        card_id=card_id,
        student_id=claims["user_id"],
        role=claims["role"],
        rating=body.rating,
        review_duration_ms=body.review_duration_ms,
    )
    return ReviewResponse(
        card_id=card_id,
        rating=body.rating,
        new_stability=scheduling["new_stability"],
        new_difficulty=scheduling["new_difficulty"],
        next_due=scheduling["next_due"],
        new_state=scheduling["new_state"],
    )


@router.delete("/{card_id}", status_code=204)
async def delete_flashcard(
    card_id: UUID,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[FlashcardService, Depends(_get_flashcard_service)],
) -> None:
    await service.delete_card(
        card_id=card_id,
        student_id=claims["user_id"],
        role=claims["role"],
    )
