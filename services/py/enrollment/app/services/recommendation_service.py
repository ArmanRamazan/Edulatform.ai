from __future__ import annotations

from uuid import UUID

from app.repositories.recommendation_repo import RecommendationRepository


class RecommendationService:
    def __init__(self, repo: RecommendationRepository) -> None:
        self._repo = repo

    async def get_similar_courses(
        self, course_id: UUID, limit: int = 5
    ) -> list[dict]:
        return await self._repo.get_similar_courses(course_id, limit)

    async def get_personalized_recommendations(
        self, user_id: UUID, limit: int = 10
    ) -> list[dict]:
        return await self._repo.get_personalized_recommendations(user_id, limit)
