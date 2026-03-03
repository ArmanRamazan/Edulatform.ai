from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


@dataclass(frozen=True)
class Pretest:
    id: UUID
    user_id: UUID
    course_id: UUID
    started_at: datetime
    completed_at: datetime | None
    status: str


@dataclass(frozen=True)
class PretestAnswer:
    id: UUID
    pretest_id: UUID
    concept_id: UUID
    question: str
    user_answer: str | None
    correct_answer: str
    is_correct: bool | None
    created_at: datetime


class AnswerSubmit(BaseModel):
    answer_id: UUID
    answer: str = Field(min_length=1, max_length=500)


class PretestStartResponse(BaseModel):
    pretest_id: UUID
    question: str
    concept_id: UUID
    answer_id: UUID
    total_concepts: int


class AnswerNextResponse(BaseModel):
    next_question: str | None = None
    concept_id: UUID | None = None
    answer_id: UUID | None = None
    progress: float
    completed: bool = False
    results: PretestResultsResponse | None = None


class ConceptResult(BaseModel):
    concept_id: UUID
    name: str
    mastery: float
    tested: bool


class PretestResultsResponse(BaseModel):
    course_id: UUID
    concepts: list[ConceptResult]
    overall_readiness: float
