from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel

from app.domain.lesson import LessonResponse
from app.domain.module import ModuleResponse


class CourseLevel(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


@dataclass(frozen=True)
class Course:
    id: UUID
    teacher_id: UUID
    title: str
    description: str
    is_free: bool
    price: Decimal | None
    duration_minutes: int
    level: CourseLevel
    created_at: datetime
    avg_rating: Decimal | None = None
    review_count: int = 0
    category_id: UUID | None = None


class CourseCreate(BaseModel):
    title: str
    description: str = ""
    is_free: bool = True
    price: Decimal | None = None
    duration_minutes: int = 0
    level: CourseLevel = CourseLevel.BEGINNER
    category_id: UUID | None = None


class CourseUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    is_free: bool | None = None
    price: Decimal | None = None
    duration_minutes: int | None = None
    level: CourseLevel | None = None
    category_id: UUID | None = None


class CourseResponse(BaseModel):
    id: UUID
    teacher_id: UUID
    title: str
    description: str
    is_free: bool
    price: Decimal | None
    duration_minutes: int
    level: CourseLevel
    created_at: datetime
    avg_rating: Decimal | None = None
    review_count: int = 0
    category_id: UUID | None = None


class CourseListResponse(BaseModel):
    items: list[CourseResponse]
    total: int
    next_cursor: str | None = None


class CurriculumModule(BaseModel):
    id: UUID
    course_id: UUID
    title: str
    order: int
    created_at: datetime
    lessons: list[LessonResponse]


class CurriculumResponse(BaseModel):
    course: CourseResponse
    modules: list[CurriculumModule]
    total_lessons: int


class CourseAnalytics(BaseModel):
    course_id: UUID
    title: str
    avg_rating: Decimal | None
    review_count: int
    module_count: int
    lesson_count: int


class TeacherAnalyticsSummary(BaseModel):
    total_courses: int
    total_lessons: int
    avg_rating: Decimal | None
    total_reviews: int
    courses: list[CourseAnalytics]
