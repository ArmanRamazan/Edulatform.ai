from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


@dataclass(frozen=True)
class Quiz:
    id: UUID
    lesson_id: UUID
    course_id: UUID
    teacher_id: UUID
    created_at: datetime


@dataclass(frozen=True)
class Question:
    id: UUID
    quiz_id: UUID
    text: str
    options: list[str]
    correct_index: int
    explanation: str | None
    order: int


@dataclass(frozen=True)
class QuizAttempt:
    id: UUID
    quiz_id: UUID
    student_id: UUID
    answers: list[int]
    score: float
    completed_at: datetime


class QuestionCreate(BaseModel):
    text: str
    options: list[str] = Field(min_length=2, max_length=6)
    correct_index: int = Field(ge=0)
    explanation: str | None = None


class QuizCreate(BaseModel):
    lesson_id: UUID
    course_id: UUID
    questions: list[QuestionCreate] = Field(min_length=1, max_length=20)


class QuestionResponse(BaseModel):
    id: UUID
    text: str
    options: list[str]
    order: int


class QuestionWithAnswer(BaseModel):
    id: UUID
    text: str
    options: list[str]
    correct_index: int
    explanation: str | None
    order: int


class QuizResponse(BaseModel):
    id: UUID
    lesson_id: UUID
    course_id: UUID
    questions: list[QuestionResponse]
    created_at: datetime


class AttemptSubmit(BaseModel):
    answers: list[int]


class QuestionResult(BaseModel):
    question_id: UUID
    selected: int
    correct_index: int
    is_correct: bool
    explanation: str | None


class AttemptResponse(BaseModel):
    id: UUID
    quiz_id: UUID
    score: float
    total_questions: int
    correct_count: int
    results: list[QuestionResult]
    completed_at: datetime


class AttemptSummary(BaseModel):
    id: UUID
    score: float
    completed_at: datetime


class AttemptListResponse(BaseModel):
    items: list[AttemptSummary]
    total: int
