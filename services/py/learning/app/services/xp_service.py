from __future__ import annotations

from uuid import UUID

from app.domain.xp import XP_REWARDS, XpEvent, XpEventResponse, XpSummaryResponse
from app.repositories.xp_repo import XpRepository


class XpService:
    def __init__(self, repo: XpRepository) -> None:
        self._repo = repo

    async def award(
        self, user_id: UUID, action: str, course_id: UUID | None = None,
    ) -> XpEvent:
        if action not in XP_REWARDS:
            raise ValueError(f"Unknown XP action: {action}")
        points = XP_REWARDS[action]
        return await self._repo.create_event(user_id, action, points, course_id)

    async def get_total(self, user_id: UUID) -> int:
        return await self._repo.get_total(user_id)

    async def get_summary(
        self, user_id: UUID, limit: int = 20, offset: int = 0,
    ) -> XpSummaryResponse:
        total = await self._repo.get_total(user_id)
        events = await self._repo.get_history(user_id, limit, offset)
        return XpSummaryResponse(
            total_xp=total,
            events=[
                XpEventResponse(
                    action=e.action,
                    points=e.points,
                    course_id=e.course_id,
                    created_at=e.created_at,
                )
                for e in events
            ],
        )
