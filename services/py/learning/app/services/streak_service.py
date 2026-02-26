from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from app.domain.streak import Streak, StreakResponse
from app.repositories.streak_repo import StreakRepository


class StreakService:
    def __init__(self, repo: StreakRepository) -> None:
        self._repo = repo

    async def record_activity(self, user_id: UUID) -> Streak:
        existing = await self._repo.get_by_user(user_id)

        if existing is None:
            return await self._repo.upsert(
                user_id=user_id, current_streak=1, longest_streak=1,
            )

        today = date.today()
        if existing.last_activity_date == today:
            return existing

        yesterday = today - timedelta(days=1)
        if existing.last_activity_date == yesterday:
            new_current = existing.current_streak + 1
        else:
            new_current = 1

        new_longest = max(new_current, existing.longest_streak)

        return await self._repo.upsert(
            user_id=user_id,
            current_streak=new_current,
            longest_streak=new_longest,
        )

    async def get_streak(self, user_id: UUID) -> StreakResponse:
        existing = await self._repo.get_by_user(user_id)

        if existing is None:
            return StreakResponse(
                current_streak=0,
                longest_streak=0,
                last_activity_date=None,
                active_today=False,
            )

        today = date.today()
        yesterday = today - timedelta(days=1)
        is_alive = existing.last_activity_date >= yesterday
        active_today = existing.last_activity_date == today

        return StreakResponse(
            current_streak=existing.current_streak if is_alive else 0,
            longest_streak=existing.longest_streak,
            last_activity_date=existing.last_activity_date,
            active_today=active_today,
        )
