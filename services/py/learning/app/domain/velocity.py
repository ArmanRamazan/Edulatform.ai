from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class WeeklyConceptCount(BaseModel):
    week_start: str
    count: int


class WeeklyQuizScore(BaseModel):
    week_start: str
    avg_score: float


class CourseProgress(BaseModel):
    course_id: str
    total_concepts: int
    mastered: int
    mastery_pct: float
    estimated_weeks_left: float | None


class VelocityResponse(BaseModel):
    concepts_mastered_this_week: int
    concepts_mastered_last_week: int
    trend: Literal["up", "down", "stable"]
    quiz_score_trend: list[WeeklyQuizScore]
    flashcard_retention_rate: float
    streak_days: int
    course_progress: list[CourseProgress]
