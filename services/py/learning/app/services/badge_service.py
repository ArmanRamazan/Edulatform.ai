from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

import structlog

from app.domain.badge import (
    BADGE_DEFINITIONS,
    Badge,
    BadgeListResponse,
    BadgeResponse,
)
from app.repositories.badge_repo import BadgeRepository

if TYPE_CHECKING:
    from app.services.activity_service import ActivityService

logger = structlog.get_logger()


class BadgeService:
    def __init__(
        self, repo: BadgeRepository, activity_service: ActivityService | None = None,
    ) -> None:
        self._repo = repo
        self._activity_service = activity_service

    async def try_unlock(self, user_id: UUID, badge_type: str) -> Badge:
        if badge_type not in BADGE_DEFINITIONS:
            raise ValueError(f"Unknown badge type: {badge_type}")
        badge = await self._repo.create(user_id, badge_type)

        if self._activity_service is not None:
            try:
                from app.domain.activity import ActivityType
                await self._activity_service.record(
                    user_id=user_id,
                    activity_type=ActivityType.badge_earned,
                    payload={"badge_type": badge_type},
                )
            except Exception:
                logger.warning("activity_record_failed", badge_type=badge_type)

        return badge

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
