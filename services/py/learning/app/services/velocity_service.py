from __future__ import annotations

from typing import Literal
from uuid import UUID

from app.repositories.velocity_repo import VelocityRepository


class VelocityService:
    def __init__(self, repo: VelocityRepository) -> None:
        self._repo = repo

    async def get_velocity(self, user_id: UUID) -> dict:
        weekly_concepts = await self._repo.get_concepts_mastered_by_week(user_id)
        quiz_trend = await self._repo.get_quiz_score_trend(user_id)
        retention = await self._repo.get_flashcard_retention_rate(user_id)
        streak = await self._repo.get_learning_streak(user_id)
        courses = await self._repo.get_course_progress(user_id)

        this_week, last_week = self._extract_recent_weeks(weekly_concepts)
        trend = self._compute_trend(this_week, last_week)
        avg_per_week = self._avg_concepts_per_week(weekly_concepts)
        progress = self._build_course_progress(courses, avg_per_week)

        return {
            "concepts_mastered_this_week": this_week,
            "concepts_mastered_last_week": last_week,
            "trend": trend,
            "quiz_score_trend": quiz_trend,
            "flashcard_retention_rate": retention,
            "streak_days": streak,
            "course_progress": progress,
        }

    @staticmethod
    def _extract_recent_weeks(weekly_concepts: list[dict]) -> tuple[int, int]:
        if not weekly_concepts:
            return 0, 0
        this_week = weekly_concepts[-1]["count"]
        last_week = weekly_concepts[-2]["count"] if len(weekly_concepts) >= 2 else 0
        return this_week, last_week

    @staticmethod
    def _compute_trend(this_week: int, last_week: int) -> Literal["up", "down", "stable"]:
        if this_week > last_week:
            return "up"
        if this_week < last_week:
            return "down"
        return "stable"

    @staticmethod
    def _avg_concepts_per_week(weekly_concepts: list[dict]) -> float:
        if not weekly_concepts:
            return 0.0
        total = sum(w["count"] for w in weekly_concepts)
        return total / len(weekly_concepts)

    @staticmethod
    def _build_course_progress(
        courses: list[dict], avg_per_week: float,
    ) -> list[dict]:
        result = []
        for c in courses:
            total = c["total_concepts"]
            mastered = c["mastered"]
            remaining = total - mastered

            if total == 0:
                mastery_pct = 0.0
                estimated = None
            else:
                mastery_pct = round(mastered / total * 100, 1)
                if remaining == 0:
                    estimated = 0.0
                elif avg_per_week <= 0:
                    estimated = None
                else:
                    estimated = round(remaining / avg_per_week, 1)

            result.append({
                "course_id": c["course_id"],
                "total_concepts": total,
                "mastered": mastered,
                "mastery_pct": mastery_pct,
                "estimated_weeks_left": estimated,
            })
        return result
