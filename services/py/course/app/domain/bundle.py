from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.domain.course import Course, CourseResponse


@dataclass(frozen=True)
class CourseBundle:
    id: UUID
    teacher_id: UUID
    title: str
    description: str
    price: Decimal
    discount_percent: int
    is_active: bool
    created_at: datetime


@dataclass(frozen=True)
class BundleCourse:
    id: UUID
    bundle_id: UUID
    course_id: UUID


@dataclass(frozen=True)
class BundleWithCourses:
    bundle: CourseBundle
    courses: list[Course]


class BundleCreate(BaseModel):
    title: str
    description: str = ""
    price: Decimal
    discount_percent: int
    course_ids: list[UUID]


class BundleUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    price: Decimal | None = None
    discount_percent: int | None = None


class BundleResponse(BaseModel):
    id: UUID
    teacher_id: UUID
    title: str
    description: str
    price: Decimal
    discount_percent: int
    is_active: bool
    created_at: datetime
    courses: list[CourseResponse]


class BundleListResponse(BaseModel):
    items: list[BundleResponse]
    total: int
