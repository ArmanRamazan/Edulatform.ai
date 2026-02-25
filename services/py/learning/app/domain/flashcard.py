from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


@dataclass(frozen=True)
class Flashcard:
    id: UUID
    student_id: UUID
    course_id: UUID
    concept: str
    answer: str
    source_type: str | None
    source_id: UUID | None
    stability: float
    difficulty: float
    due: datetime
    last_review: datetime | None
    reps: int
    lapses: int
    state: int  # 0=New, 1=Learning, 2=Review, 3=Relearning
    created_at: datetime


@dataclass(frozen=True)
class ReviewLog:
    id: UUID
    card_id: UUID
    rating: int  # 1=Again, 2=Hard, 3=Good, 4=Easy
    review_duration_ms: int | None
    reviewed_at: datetime


class FlashcardCreate(BaseModel):
    course_id: UUID
    concept: str = Field(min_length=1, max_length=500)
    answer: str = Field(min_length=1, max_length=2000)
    source_type: str | None = None
    source_id: UUID | None = None


class ReviewSubmit(BaseModel):
    rating: int = Field(ge=1, le=4)  # 1=Again, 2=Hard, 3=Good, 4=Easy
    review_duration_ms: int | None = None


class FlashcardResponse(BaseModel):
    id: UUID
    course_id: UUID
    concept: str
    answer: str
    source_type: str | None
    stability: float
    difficulty: float
    due: datetime
    state: int
    reps: int
    lapses: int
    created_at: datetime


class ReviewResponse(BaseModel):
    card_id: UUID
    rating: int
    new_stability: float
    new_difficulty: float
    next_due: datetime
    new_state: int


class DueCardsResponse(BaseModel):
    items: list[FlashcardResponse]
    total: int
