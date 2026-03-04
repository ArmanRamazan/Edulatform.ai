from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class CourseRecommendation(BaseModel):
    course_id: UUID
    co_enrollment_count: int


class RecommendationListResponse(BaseModel):
    items: list[CourseRecommendation]
