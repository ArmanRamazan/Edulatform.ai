from __future__ import annotations

from uuid import UUID

from app.domain.badge import (
    BADGE_DEFINITIONS,
    Badge,
    BadgeListResponse,
    BadgeResponse,
)
from app.repositories.badge_repo import BadgeRepository


class BadgeService:
    def __init__(self, repo: BadgeRepository) -> None:
        self._repo = repo

    async def try_unlock(self, user_id: UUID, badge_type: str) -> Badge:
        if badge_type not in BADGE_DEFINITIONS:
            raise ValueError(f"Unknown badge type: {badge_type}")
        return await self._repo.create(user_id, badge_type)

    async def get_badges(self, user_id: UUID) -> BadgeListResponse:
        badges = await self._repo.get_all(user_id)
        return BadgeListResponse(
            badges=[
                BadgeResponse(
                    badge_type=b.badge_type,
                    description=BADGE_DEFINITIONS[b.badge_type],
                    unlocked_at=b.unlocked_at,
                )
                for b in badges
            ],
            total=len(badges),
        )

    async def check_streak_badge(
        self, user_id: UUID, current_streak: int,
    ) -> Badge | None:
        if current_streak >= 7:
            return await self.try_unlock(user_id, "streak_7")
        return None

    async def check_quiz_ace_badge(
        self, user_id: UUID, score: float,
    ) -> Badge | None:
        if score >= 1.0:
            return await self.try_unlock(user_id, "quiz_ace")
        return None

    async def check_mastery_badge(
        self, user_id: UUID, mastery: float,
    ) -> Badge | None:
        if mastery >= 1.0:
            return await self.try_unlock(user_id, "mastery_100")
        return None
