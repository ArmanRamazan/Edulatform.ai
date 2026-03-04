from __future__ import annotations

from uuid import UUID

from app.domain.activity import Activity, ActivityType
from app.repositories.activity_repo import ActivityRepository


class ActivityService:
    def __init__(self, repo: ActivityRepository) -> None:
        self._repo = repo

    async def record(
        self, user_id: UUID, activity_type: ActivityType, payload: dict,
    ) -> Activity:
        return await self._repo.record_activity(
            user_id, activity_type.value, payload,
        )

    async def get_my_activity(
        self, user_id: UUID, limit: int = 20, offset: int = 0,
    ) -> list[Activity]:
        return await self._repo.get_user_activities(user_id, limit, offset)

    async def get_social_feed(
        self, user_ids: list[UUID], limit: int = 20, offset: int = 0,
    ) -> list[Activity]:
        if not user_ids:
            return []
        return await self._repo.get_feed_for_users(user_ids, limit, offset)
